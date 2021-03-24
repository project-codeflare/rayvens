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
from rayvens.core.mode import mode, RayKamelExecLocation
from rayvens.core import kubernetes
from rayvens.core import kamel
from rayvens.core import utils
from rayvens.core.catalog import construct_source, construct_sink


def start(camel_mode):
    camel = None
    mode.connector = 'http'
    if camel_mode == 'local':
        mode.location = RayKamelExecLocation.LOCAL
        camel = CamelAnyNode(mode)
    elif camel_mode == 'mixed.operator':
        mode.location = RayKamelExecLocation.MIXED
        camel = CamelAnyNode(mode)
    elif camel_mode == 'cluster.operator':
        mode.location = RayKamelExecLocation.CLUSTER
        camel = CamelAnyNode(mode)
    else:
        raise RuntimeError("Unsupported camel mode.")
    return camel


class CamelAnyNode:
    def __init__(self, mode):
        self.mode = mode

        # TODO: add node and process id to unique name of integrations and
        # services.
        self.endpoint_id = -1
        self.integration_id = -1
        self.service_id = -1

        # List of command invocations used to clean-up the environment.
        self.invocations = {}

        # List of services used to clean-up the environment.
        self.services = {}

        # The Ray Serve backend used for Sinks. Sink are a special case and
        # can use one backend to support multiple sinks.
        self.kamel_backend = None

        # Start server is using a backend.
        if self.mode.hasRayServeConnector():
            serve.start()

    def add_source(self, stream, source, handle):
        # Get integration name.
        integration_name = self._get_integration_name(stream.name)

        # Construct endpoint.
        route = f'/{stream.name}'
        if 'route' in source and source['route'] is not None:
            route = source['route']

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
            endpoint_name = self._get_endpoint_name(stream.name)

            # Create backend for this topic.
            source_backend = KamelBackend(self.mode, topic=handle)

            # Create endpoint.
            source_backend.createProxyEndpoint(endpoint_name, route,
                                               integration_name)

        # Start running the source integration.
        source_invocation = kamel.run([integration_content],
                                      self.mode,
                                      integration_name,
                                      integration_as_files=False,
                                      inverted_http=inverted)
        # self.invocations[source_invocation] = integration_name
        self.invocations[integration_name] = source_invocation

        # Set up source for the HTTP connector case.
        if self.mode.hasHTTPConnector():
            server_address = self.mode.getQuarkusHTTPServer(integration_name)
            send_to_helper = SendToHelper()
            send_to_helper.send_to(handle, server_address, route)

        return self._await_start(integration_name)

    def add_sink(self, stream, sink, handle):
        # Compose integration name.
        integration_name = self._get_integration_name(stream.name)

        # Extract config.
        route = f'/{stream.name}'
        if 'route' in sink and sink['route'] is not None:
            route = sink['route']

        use_backend = False
        if 'use_backend' in sink and sink['use_backend'] is not None:
            use_backend = sink['use_backend']

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
        # self.invocations[sink_invocation] = integration_name
        self.invocations[integration_name] = sink_invocation

        # If running in mixed mode, i.e. Ray locally and kamel in the cluster,
        # then we have to also start a service the allows outside processes to
        # send data to the sink.
        if self.mode.isMixed():
            service_name = self._get_service_name("kind-external-connector")
            kubernetes.createExternalServiceForKamel(mode, service_name,
                                                     integration_name)
            self.services[integration_name] = service_name

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
        handle.send_to.remote(helper, stream.name)

        return self._await_start(integration_name)

    def disconnect(self, integration_name):
        # Check integration name is valid.
        if integration_name not in self.invocations:
            raise RuntimeError(f'{integration_name} is invalid')

        # Retrieve invocation.
        invocation = self.invocations[integration_name]

        # If kamel is running the cluster then use kamel delete to
        # terminate the integration.
        if self.mode.isCluster() or self.mode.isMixed():
            outcome = True

            # First we terminate any services associated with the integration.
            if integration_name in self.services:
                outcome = kubernetes.deleteService(
                    self.mode, self.services[integration_name])
            if not outcome:
                raise RuntimeWarning(
                    f'{self.services[integration_name]} for {integration_name}'
                    'could not be terminated')

            # Terminate the integration itself.
            if not kamel.delete(invocation, integration_name):
                outcome = False

            return outcome

        # If integration is running locally we only need to kill the
        # process that runs it.
        if self.mode.isLocal():
            invocation.kill()
            return True

        return False

    def disconnect_all(self):
        # Disconnect all the integrations.
        outcome = True
        for integration_name in self.invocations:
            if not self.disconnect(integration_name):
                outcome = False

        return outcome

    def _await_start(self, integration_name):
        # TODO: remove this once we enable this for local mode.
        if self.mode.isLocal():
            return True

        # Wait for pod to start.
        pod_is_running, pod_name = kubernetes.getPodRunningStatus(
            self.mode, integration_name)
        if pod_is_running:
            print(f'Pod {pod_name} is running.')
        else:
            print('Pod did not run correctly.')
            return False

        # Wait for integration to be installed. Since we now know that the pod
        # is running we can use that to check that the integration is installed
        # correctly.
        integration_is_running = kubernetes.getIntegrationStatus(
            self.mode, pod_name)
        if integration_is_running:
            print(f'Integration {integration_name} is running.')
        else:
            print('Integration did not start correctly.')

        return integration_is_running

    def await_start_all(self, stream):
        # Await for all sinks to start.
        for sink_name in stream._sinks:
            self._await_start(sink_name)
        # Await for all sources to start.
        for source_name in stream._sources:
            self._await_start(source_name)

    def _get_endpoint_name(self, name):
        self.endpoint_id += 1
        return "_".join(["endpoint", name, str(self.endpoint_id)])

    def _get_integration_name(self, name):
        self.integration_id += 1
        return "-".join(["integration", name, str(self.integration_id)])

    def _get_service_name(self, name):
        self.service_id += 1
        return "-".join(["service", name, str(self.service_id)])


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
