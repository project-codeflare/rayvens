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
from ray import serve
from rayvens.core.kamel_backend import KamelBackend
from rayvens.core import kubernetes
from rayvens.core import kamel
from rayvens.core import utils
from rayvens.core import common
from rayvens.core.catalog import construct_source, construct_sink
from rayvens.core.common import await_start
from rayvens.core.integration import Integration


def start(camel_mode):
    return Camel(common.get_run_mode(camel_mode))


class Camel:
    def __init__(self, mode):
        self.mode = mode

        # The Ray Serve backend used for Sinks. Sink are a special case and
        # can use one backend to support multiple sinks.
        self.kamel_backend = None

        # Start server is using a backend.
        serve.start()

    def add_source(self, stream, source, source_name):
        # Construct integration
        integration = Integration(stream.name, source_name, source)

        # Construct endpoint. First, get route:
        route = integration.route()

        # Determine the `to` endpoint value made up of a base address and
        # a custom route provided by the user. The computation depends on
        # the connector type used for the implementation.
        server_pod_name = ""
        if self.mode.isCluster():
            server_pod_name = utils.get_server_pod_name()
        endpoint_base = self.mode.getQuarkusHTTPServer(server_pod_name,
                                                       serve_source=True)

        # Construct integration source code. When the ray serve connector is
        # not enabled, use an HTTP inverted connection.
        integration_content = construct_source(source,
                                               f'{endpoint_base}{route}')

        # Set endpoint and integration names.
        endpoint_name = self._get_endpoint_name(integration.integration_name)

        # Create backend for this topic.
        source_backend = KamelBackend(self.mode, topic=stream.actor)

        # Create endpoint.
        source_backend.createProxyEndpoint(endpoint_name, route,
                                           integration.integration_name)

        # Start running the source integration.
        source_invocation = kamel.run([integration_content],
                                      self.mode,
                                      integration.integration_name,
                                      integration_as_files=False)
        integration.invocation = source_invocation

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

        if self.mode.isMixed():
            integration.service_name = common.create_externalizing_service(
                self.mode, integration)

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
