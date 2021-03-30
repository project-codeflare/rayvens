#
# Copyright IBM Corporation 2021
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import requests
import ray
import time
import threading
from ray import serve
from rayvens.core.kamel_backend import KamelBackend
from rayvens.core.mode import mode, RayvensMode
from rayvens.core import kubernetes
from rayvens.core import kamel
from rayvens.core import utils
from rayvens.core.catalog import construct_source, construct_sink
from rayvens.core.common import await_start
from rayvens.core.integration import Integration


def start(camel_mode):
    camel = None
    mode.connector = 'http'
    if camel_mode == 'local.local':
        mode.run_mode = RayvensMode.LOCAL
        camel = Camel(mode)
    elif camel_mode == 'mixed.operator':
        mode.run_mode = RayvensMode.MIXED_OPERATOR
        camel = Camel(mode)
    elif camel_mode == 'operator':
        mode.run_mode = RayvensMode.CLUSTER_OPERATOR
        camel = Camel(mode)
    else:
        raise RuntimeError("Unsupported camel mode.")
    return camel


class Camel:
    def __init__(self, mode):
        self.mode = mode

        # The Ray Serve backend used for Sinks. Sink are a special case and
        # can use one backend to support multiple sinks.
        self.kamel_backend = None

        # Start server is using a backend.
        if self.mode.hasRayServeConnector():
            serve.start()

    def add_source(self, stream, source, source_name):
        # Construct integration
        integration = Integration(stream.name, source_name, source)

        # Construct endpoint. First, get route:
        route = integration.route()

        # Determine the `to` endpoint value made up of a base address and
        # a custom route provided by the user. The computation depends on
        # the connector type used for the implementation.
        if self.mode.hasRayServeConnector():
            # TODO: move this code inside the Execution class.
            server_pod_name = ""
            if self.mode.isCluster():
                server_pod_name = utils.get_server_pod_name()
            endpoint_base = self.mode.getQuarkusHTTPServer(server_pod_name,
                                                           serve_source=True)
        elif self.mode.hasHTTPConnector():
            endpoint_base = "platform-http:"
        else:
            raise RuntimeError(
                f'{self.mode.connector} connector is unsupported')
        endpoint = f'{endpoint_base}{route}'

        # Construct integration source code. When the ray serve connector is
        # not enabled, use an HTTP inverted connection.
        inverted = self.mode.hasHTTPConnector()
        integration_content = construct_source(source,
                                               endpoint,
                                               inverted=inverted)

        if self.mode.hasRayServeConnector():
            # Set endpoint and integration names.
            endpoint_name = self._get_endpoint_name(
                integration.integration_name)

            # Create backend for this topic.
            source_backend = KamelBackend(self.mode, topic=stream.actor)

            # Create endpoint.
            source_backend.createProxyEndpoint(endpoint_name, route,
                                               integration.integration_name)

        # Start running the source integration.
        source_invocation = kamel.run([integration_content],
                                      self.mode,
                                      integration.integration_name,
                                      integration_as_files=False,
                                      inverted_http=inverted)
        integration.invocation = source_invocation

        # Set up source for the HTTP connector case.
        if self.mode.hasHTTPConnector():
            server_address = self.mode.getQuarkusHTTPServer(
                integration.integration_name)
            send_to_helper = SendToHelper()
            send_to_helper.send_to(stream.actor, server_address, route)

        if not await_start(self.mode, integration.integration_name):
            raise RuntimeError('Could not start source')
        return integration

    def add_sink(self, stream, sink, sink_name):
        # Construct integration
        integration = Integration(stream.name, sink_name, sink)

        # Extract integration properties:
        route = integration.route()
        use_backend = integration.use_backend()
        integration_name = integration.integration_name

        # Get integration source code.
        integration_content = construct_sink(sink, f'platform-http:{route}')

        # Create backend if one hasn't been created so far.
        if use_backend and self.kamel_backend is None:
            self.kamel_backend = KamelBackend(self.mode)

        # Start running the integration.
        sink_invocation = kamel.run([integration_content],
                                    self.mode,
                                    integration_name,
                                    integration_as_files=False)
        integration.invocation = sink_invocation

        # If running in mixed mode, i.e. Ray locally and kamel in the cluster,
        # then we have to also start a service the allows outside processes to
        # send data to the sink.
        if self.mode.isMixed():
            service_name = self._get_service_name(integration_name)
            kubernetes.createExternalServiceForKamel(mode, service_name,
                                                     integration_name)
            integration.service = service_name

        if use_backend:
            endpoint_name = self._get_endpoint_name(stream.name)
            self.kamel_backend.createProxyEndpoint(endpoint_name, route,
                                                   integration_name)

            helper = HelperWithBackend.remote(self.kamel_backend,
                                              serve.get_handle(endpoint_name),
                                              endpoint_name)
        else:
            helper = Helper.remote(
                self.mode.getQuarkusHTTPServer(integration_name) + route)
        stream.actor.send_to.remote(helper, sink_name)

        # Wait for integration to finish.
        if not await_start(self.mode, integration_name):
            raise RuntimeError('Could not start sink')

        return integration

    def disconnect(self, integration):
        if self.mode.isCluster() or self.mode.isMixed():
            # If kamel is running the cluster then use kamel delete to
            # terminate the integration. First we terminate any services
            # associated with the integration.
            if integration.service is not None:
                if not kubernetes.deleteService(self.mode,
                                                integration.service):
                    raise RuntimeError(
                        f'Service with name {integration.service} for'
                        '{integration.integration_name} could not be'
                        'terminated')

            # Terminate the integration itself.
            if not kamel.delete(integration.invocation,
                                integration.integration_name):
                raise RuntimeError(
                    f'Failed to terminate {integration.integration_name}')
        elif self.mode.isLocal():
            # If integration is running locally we only need to kill the
            # process that runs it.
            integration.invocation.kill()
        else:
            raise RuntimeError('Unknown run mode')

    def _get_endpoint_name(self, integration_name):
        return "_".join(["endpoint", integration_name])

    def _get_service_name(self, integration_name):
        return "-".join(["service", integration_name])


class SendToHelper:
    def send_to(self, handle, server_address, route):
        def append():
            while True:
                try:
                    response = requests.get(f'{server_address}{route}')
                    if response.status_code != 200:
                        time.sleep(1)
                        continue
                    handle.append.remote(response.text)
                except requests.exceptions.ConnectionError:
                    time.sleep(1)

        threading.Thread(target=append).start()


@ray.remote(num_cpus=0)
class HelperWithBackend:
    def __init__(self, backend, endpoint_handle, endpoint_name):
        self.backend = backend
        self.endpoint_name = endpoint_name
        self.endpoint_handle = endpoint_handle

    def append(self, data):
        if data is not None:
            answer = self.backend.postToProxyEndpointHandle(
                self.endpoint_handle, self.endpoint_name, data)
            print(answer)


@ray.remote(num_cpus=0)
class Helper:
    def __init__(self, url):
        self.url = url

    def append(self, data):
        if data is not None:
            requests.post(self.url, data)
