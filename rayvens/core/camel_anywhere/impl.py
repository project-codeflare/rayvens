import atexit
import ray
from ray import serve
from rayvens.core.camel_anywhere.kamel_backend import KamelBackend
from rayvens.core.camel_anywhere.mode import mode, RayKamelExecLocation
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
        self.invocations = []

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
        self.invocations.append(source_invocation)

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

        # Create backend if one hasn't been created so far.
        if self.kamel_backend is None:
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
        self.invocations.append(sink_invocation)

        endpoint_name = self._get_endpoint_name(name)
        self.kamel_backend.createProxyEndpoint(self.client, endpoint_name,
                                               route, integration_name)

        helper = EndpointHelper.remote(self.kamel_backend,
                                       self.client.get_handle(endpoint_name),
                                       endpoint_name)
        topic.send_to.remote(helper, name)

    def exit(self):
        # TODO: delete endpoints.
        # This deletes all the integrations.
        for invocation in self.invocations:
            if self.mode.isCluster() or self.mode.isMixed():
                kamel.delete(invocation)
            elif self.mode.isLocal():
                invocation.kill.remote()
            else:
                raise RuntimeError("Unreachable")
        # TODO: check that the invocation does not need to be killed when
        # running in the Cluster or Mixed modes.

    def _get_endpoint_name(self, name):
        self.endpoint_id += 1
        return "_".join(["endpoint", name, str(self.endpoint_id)])

    def _get_integration_name(self, name):
        self.integration_id += 1
        return "-".join(["integration", name, str(self.integration_id)])


@ray.remote(num_cpus=0)
class EndpointHelper:
    def __init__(self, backend, endpoint_handle, endpoint_name):
        self.backend = backend
        self.endpoint_name = endpoint_name
        self.endpoint_handle = endpoint_handle

    def append(self, data):
        if data is not None:
            answer = self.backend.postToProxyEndpointHandle(
                self.endpoint_handle, self.endpoint_name, data)
            print(answer)
