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

import atexit
import requests
import ray
from ray import serve
from rayvens.core.camel_anywhere.kamel_backend import KamelBackend
from rayvens.core.camel_anywhere.mode import mode, RayKamelExecLocation
from rayvens.core.camel_anywhere import kubernetes
from rayvens.core.camel_anywhere import kamel
from rayvens.core.validation import Validation
from rayvens.core.utils import utils
from rayvens.core.catalog import construct_source, construct_sink


def start(prefix, camel_mode):
    camel = None
    if camel_mode == 'local':
        mode.location = RayKamelExecLocation.LOCAL
        camel = CamelAnyNode.remote(mode)
    elif camel_mode == 'mixed.operator':
        mode.location = RayKamelExecLocation.MIXED
        camel = CamelAnyNode.remote(mode)
    elif camel_mode == 'cluster.operator':
        mode.location = RayKamelExecLocation.CLUSTER
        camel = CamelAnyNode.options(resources={'head': 1}).remote(mode)
    else:
        raise RuntimeError("Unsupported camel mode.")

    # Setup what happens at exit.
    atexit.register(camel.exit.remote)
    return camel


@ray.remote(num_cpus=0)
class CamelAnyNode:
    def __init__(self, mode):
        self.mode = mode
        if self.mode.isCluster():
            self.client = serve.start(http_options={
                'host': '0.0.0.0',
                'location': 'EveryNode'
            })
        else:
            self.client = serve.start()
        self.kamel_backend = None
        self.endpoint_id = -1
        self.integration_id = -1
        self.service_id = -1
        self.validation = Validation()
        self.invocations = {}
        self.services = []

    def add_stream(self, stream, name):
        self.validation.add_stream(stream, name)

    def add_source(self, stream, source):
        # Get stream name.
        name = self.validation.get_stream_name(stream)

        # Get integration name.
        integration_name = self._get_integration_name(name)

        # Construct endpoint.
        route = f'/{name}'
        if 'route' in source and source['route'] is not None:
            route = source['route']

        server_pod_name = ""
        if self.mode.isCluster():
            server_pod_name = utils.get_server_pod_name()
        endpoint_base = self.mode.getQuarkusHTTPServer(server_pod_name,
                                                       source=True)
        endpoint = f'{endpoint_base}{route}'

        # Construct integration source code.
        integration_content = construct_source(source, endpoint)

        # Add source after integration configuration has been validated.
        self.validation.add_source(stream, integration_name)

        # Set endpoint and integration names.
        endpoint_name = self._get_endpoint_name(name)

        # Create backend for this topic.
        source_backend = KamelBackend(self.client, self.mode, topic=stream)

        # Create endpoint.
        source_backend.createProxyEndpoint(self.client, endpoint_name, route,
                                           integration_name)

        # Start running the source integration.
        source_invocation = kamel.run([integration_content],
                                      self.mode,
                                      integration_name,
                                      integration_as_files=False)
        self.invocations[source_invocation] = integration_name

        return integration_name

    def add_sink(self, stream, sink):
        # Get stream name.
        name = self.validation.get_stream_name(stream)

        # Compose integration name.
        integration_name = self._get_integration_name(name)

        # Extract config.
        route = f'/{name}'
        if 'route' in sink and sink['route'] is not None:
            route = sink['route']

        use_backend = False
        if 'use_backend' in sink and sink['use_backend'] is not None:
            use_backend = sink['use_backend']

        # Get integration source code.
        integration_content = construct_sink(sink, f'platform-http:{route}')

        # Add sink after integration configuration has been validated.
        self.validation.add_sink(stream, integration_name)

        # Create backend if one hasn't been created so far.
        if use_backend and self.kamel_backend is None:
            self.kamel_backend = KamelBackend(self.client, self.mode)

        # Start running the integration.
        sink_invocation = kamel.run([integration_content],
                                    self.mode,
                                    integration_name,
                                    integration_as_files=False)
        self.invocations[sink_invocation] = integration_name

        # If running in mixed mode, i.e. Ray locally and kamel in the cluster,
        # then we have to also start a service the allows outside processes to
        # send data to the sink.
        if self.mode.isMixed():
            service_name = self._get_service_name("kind-external-connector")
            kubernetes.createExternalServiceForKamel(mode, service_name,
                                                     integration_name)
            self.services.append(service_name)

        if use_backend:
            endpoint_name = self._get_endpoint_name(name)
            self.kamel_backend.createProxyEndpoint(self.client, endpoint_name,
                                                   route, integration_name)

            helper = HelperWithBackend.remote(
                self.kamel_backend, self.client.get_handle(endpoint_name),
                endpoint_name)
        else:
            helper = Helper.remote(
                self.mode.getQuarkusHTTPServer(integration_name) + route)
        stream.send_to.remote(helper, name)

        return integration_name

    def exit(self):
        # TODO: delete endpoints from Ray server.
        # This deletes all the additional services.
        for service in self.services:
            kubernetes.deleteService(self.mode, service)
        # This deletes all the integrations.
        for invocation in self.invocations:
            if self.mode.isCluster() or self.mode.isMixed():
                kamel.delete(invocation, self.invocations[invocation])
            elif self.mode.isLocal():
                invocation.kill()
            else:
                raise RuntimeError("Unreachable")
        # TODO: check that the invocation does not need to be killed when
        # running in the Cluster or Mixed modes.

    def await_start(self, integration_name):
        # TODO: remove this once we enable this for local mode.
        if self.mode.isLocal():
            return True

        # Validate integration.
        self.validation.validate_integration(integration_name)

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
        for sink_name in self.validation.get_sinks(stream):
            self.await_start(sink_name)
        # Await for all sources to start.
        for source_name in self.validation.get_sources(stream):
            self.await_start(source_name)

    def _get_endpoint_name(self, name):
        self.endpoint_id += 1
        return "_".join(["endpoint", name, str(self.endpoint_id)])

    def _get_integration_name(self, name):
        self.integration_id += 1
        return "-".join(["integration", name, str(self.integration_id)])

    def _get_service_name(self, name):
        self.service_id += 1
        return "-".join(["service", name, str(self.service_id)])


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
