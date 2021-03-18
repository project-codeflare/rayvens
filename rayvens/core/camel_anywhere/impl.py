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
from rayvens.core.utils import utils


def start(prefix, camel_mode):
    camel = None
    if camel_mode == 'local':
        mode.location = RayKamelExecLocation.LOCAL
        camel = CamelAnyNode.remote(prefix, mode)
    elif camel_mode == 'mixed':
        mode.location = RayKamelExecLocation.MIXED
        camel = CamelAnyNode.remote(prefix, mode)
    elif camel_mode == 'operator':
        mode.location = RayKamelExecLocation.CLUSTER
        camel = CamelAnyNode.options(resources={
            'head': 1
        }).remote(prefix, mode)
    else:
        raise RuntimeError("Unsupported camel mode.")

    # Setup what happens at exit.
    atexit.register(camel.exit.remote)
    return camel


@ray.remote(num_cpus=0)
class CamelAnyNode:
    def __init__(self, prefix, mode):
        self.client = serve.start(http_options={
            'host': '0.0.0.0',
            'location': 'EveryNode'
        })
        self.prefix = prefix
        self.mode = mode
        self.kamel_backend = None
        self.endpoint_id = -1
        self.integration_id = -1
        self.invocations = {}

    def add_source(self, name, topic, source):
        if 'kind' in source:
            if source['kind'] is None:
                raise TypeError('A Camel source needs a kind.')
            if source['kind'] not in ['http-source']:
                raise TypeError('Unsupported Camel source.')
        if 'url' not in source:
            raise TypeError('url field not provided.')
        source_url = source['url']
        route = f'{self.prefix}/{name}'
        if 'route' in source and source['route'] is not None:
            route = f'{self.prefix}' + source['route']
        period = source.get('period', 1000)

        # Set endpoint and integration names.
        endpoint_name = self._get_endpoint_name(name)
        integration_name = self._get_integration_name(name)

        # Create backend for this topic.
        source_backend = KamelBackend(self.client, self.mode, topic=topic)

        # Create endpoint.
        source_backend.createProxyEndpoint(self.client, endpoint_name, route,
                                           integration_name)

        if self.mode.isCluster():
            server_pod_name = utils.get_server_pod_name()

        # Endpoint address.
        endpoint_address = self.mode.getQuarkusHTTPServer(server_pod_name,
                                                          source=True)
        integration_content = [{
            'from': {
                'uri': f'timer:tick?period={period}',
                'steps': [{
                    'to': source_url
                }, {
                    'to': f'{endpoint_address}{route}'
                }]
            }
        }]

        # Start running the source integration.
        source_invocation = kamel.run([integration_content],
                                      self.mode,
                                      integration_name,
                                      integration_as_files=False)
        self.invocations[source_invocation] = integration_name

        return integration_name

    def add_sink(self, name, topic, sink):
        if 'kind' in sink:
            if sink['kind'] is None:
                raise TypeError('A Camel sink needs a kind.')
            if sink['kind'] not in ['slack-sink']:
                raise TypeError('Unsupported Camel sink.')
        route = f'/{name}'
        if 'route' in sink and sink['route'] is not None:
            route = sink['route']
        if 'channel' not in sink:
            raise TypeError('channel field not provided for sink.')
        channel = sink['channel']
        if 'webhookUrl' not in sink:
            raise TypeError('webhookUrl field not provided for sink.')
        webhookUrl = sink['webhookUrl']
        use_backend = False
        if 'use_backend' in sink and sink['use_backend'] is not None:
            use_backend = sink['use_backend']

        # Create backend if one hasn't been created so far.
        if use_backend and self.kamel_backend is None:
            self.kamel_backend = KamelBackend(self.client, self.mode)

        # Write integration code to file.
        # TODO: for now only support 1 integration content.
        integration_content = [{
            'from': {
                'uri': f'platform-http:{route}',
                'steps': [{
                    'to': f'slack:{channel}?webhookUrl={webhookUrl}',
                }]
            }
        }]

        # Start running the integration.
        integration_name = self._get_integration_name(name)
        sink_invocation = kamel.run([integration_content],
                                    self.mode,
                                    integration_name,
                                    integration_as_files=False)
        self.invocations[sink_invocation] = integration_name

        # Start running the integration.
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
        topic.send_to.remote(helper, name)

        return integration_name

    def exit(self):
        # TODO: delete endpoints.
        # This deletes all the integrations.
        for invocation in self.invocations:
            if self.mode.isCluster() or self.mode.isMixed():
                kamel.delete(invocation, self.invocations[invocation])
            elif self.mode.isLocal():
                invocation.kill.remote()
            else:
                raise RuntimeError("Unreachable")
        # TODO: check that the invocation does not need to be killed when
        # running in the Cluster or Mixed modes.

    def await_start(self, integration_name):
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

    def _get_endpoint_name(self, name):
        self.endpoint_id += 1
        return "_".join(["endpoint", name, str(self.endpoint_id)])

    def _get_integration_name(self, name):
        self.integration_id += 1
        return "-".join(["integration", name, str(self.integration_id)])


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
