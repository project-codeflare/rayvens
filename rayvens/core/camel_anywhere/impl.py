import atexit
import ray
from ray import serve
from rayvens.core.camel_anywhere.kamel_backend import KamelBackend
from rayvens.core.camel_anywhere.mode import mode, RayKamelExecLocation
from rayvens.core.camel_anywhere import kamel


def start(prefix, camel_mode):
    # if os.getenv('KUBE_POD_NAMESPACE') is not None and mode != 'local':
    #     camel = CamelAnyNode.options(resources={
    #         'head': 1
    #     }).remote(prefix, 'operator')
    # else:
    #     camel = CamelAnyNode.remote(prefix, 'local')
    # TODO: implement other
    if camel_mode == 'anywhere.local':
        mode.location = RayKamelExecLocation.LOCAL
    elif camel_mode == 'anywhere.mixed':
        mode.location = RayKamelExecLocation.MIXED
    elif camel_mode == 'anywhere.operator':
        mode.location = RayKamelExecLocation.CLUSTER
    else:
        raise RuntimeError("Unsupported camel mode.")
    camel = CamelAnyNode.remote(prefix, camel_mode, mode)
    atexit.register(camel.exit.remote)
    return camel


@ray.remote(num_cpus=0)
class CamelAnyNode:
    def __init__(self, prefix, camel_mode, mode):
        self.client = serve.start(http_options={
            'host': '0.0.0.0',
            'location': 'EveryNode'
        })
        # # self.client = serve.start()
        self.prefix = prefix
        self.camel_mode = mode
        self.mode = mode
        self.kamel_backend = None
        self.endpoint_id = -1
        self.integration_id = -1
        self.invocations = []

    def start_kamel_backend(self):
        self.kamel_backend = KamelBackend(self.client, self.mode)

    def add_source(self, name, topic, source):
        pass

    def add_sink(self, name, topic, sink):
        if sink['kind'] is None:
            raise TypeError('A Camel sink needs a kind.')
        if sink['kind'] not in ['slack-sink']:
            raise TypeError('Unsupported Camel sink.')
        channel = sink['channel']
        webhookUrl = sink['webhookUrl']
        route = sink['route']

        # Write integration code to file.
        # TODO: Get this content from a Catalog.
        # filename = f'{name}.yaml'
        integration_content = [{
            'from': {
                'uri': f'platform-http:{route}',
                'steps': [{
                    'to': f'slack:{channel}?webhookUrl={webhookUrl}',
                }]
            }
        }]
        # print("File path:", os.path.abspath(filename))
        # print("File contents:", integration)
        # with open(filename, 'w') as f:
        #     yaml.dump(integration, f)

        # Start running the integration.
        print("Start kamel run. Mode is cluster = ", self.mode.isCluster())
        integration_name = self._get_integration_name(name)
        sink_invocation = kamel.run([integration_content],
                                    self.mode,
                                    integration_name,
                                    integration_as_files=False)
        print("Append invocation to list.")
        self.invocations.append(sink_invocation)

        endpoint_name = self._get_endpoint_name(name)
        print("Create endpoint with name:", endpoint_name)
        # self.kamel_backend.removeProxyEndpoint(endpoint_name)
        self.kamel_backend.createProxyEndpoint(endpoint_name, route)

        print("Add endpoint to Topic list.")
        topic._save_endpoint_call.remote(self.post_to_endpoint, endpoint_name)

    def post_to_endpoint(camel, endpoint_name, data):
        print("Post to endpoint:", endpoint_name)
        camel.kamel_backend.postToProxyEndpoint(endpoint_name, data)

    def exit(self):
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
