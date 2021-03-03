from events import kamel
import ray
import requests

in_cluster = False
client = None


def setInCluster():
    global in_cluster
    in_cluster = True


def setClient(c):
    global client
    client = c


@ray.remote
class Topic:
    def __init__(self, name):
        self.name = name
        self.subscribers = []
        self.integrations = []

    def subscribe(self, f, name=None):
        self.subscribers.append({'f': f, 'name': name})

    def publish(self, *args, **kwargs):
        for s in self.subscribers:
            s['f'](*args, **kwargs)

    def _register(self, name, integration):
        self.integrations.append({'name': name, 'integration': integration})

    def _disconnect(self):
        self.subscribers = []
        integrations = self.integrations
        self.integrations = []
        return integrations


def addSink(name, topic, to):
    integration = kamel.Integration(name, in_cluster, [
        {'from': {'uri': f'platform-http:/{name}', 'steps': [{'to': to}]}}])
    topic.subscribe.remote(lambda data: requests.post(
        f'{integration.url()}/{name}', data), name)
    topic._register.remote(name, integration)


def addSource(name, topic, url, period=3000, prefix='/events'):
    async def publish(data):
        topic.publish.remote(await data.body())
    client.create_backend(name, publish, config={'num_replicas': 1})
    client.create_endpoint(
        name, backend=name, route=f'{prefix}/{name}', methods=['POST'])
    if in_cluster:
        endpoint = 'http://example-cluster-ray-head.ray.svc.cluster.local:8000'
    else:
        endpoint = 'http://localhost:8000'
    integration = kamel.Integration(name, in_cluster, [{'from': {'uri': f'timer:tick?period={period}', 'steps': [
        {'to': url}, {'to': f'{endpoint}{prefix}/{name}'}]}}])
    topic._register.remote(name, integration)


def disconnectAll(topic):
    integrations = ray.get(topic._disconnect.remote())
    for i in integrations:
        i['integration'].cancel()
