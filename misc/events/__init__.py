from events import kamel
import ray
import requests


def me():
    return 'http://localhost:8000'


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


def post(topic, name, to):
    integration = kamel.Integration(name, [
        {'from': {'uri': f'platform-http:/{name}', 'steps': [{'to': to}]}}])
    topic.subscribe.remote(lambda data: requests.post(
        f'{integration.url()}/{name}', data), name)
    topic._register.remote(name, integration)


def poll(client, topic, name, url, period=3000, prefix='/events'):
    async def publish(data):
        topic.publish.remote(await data.body())
    client.create_backend(name, publish)
    client.create_endpoint(
        name, backend=name, route=f'{prefix}/{name}', methods=['POST'])
    integration = kamel.Integration(name, [{'from': {'uri': f'timer:tick?period={period}', 'steps': [
        {'to': url}, {'to': f'{me()}{prefix}/{name}'}]}}])
    topic._register.remote(name, integration)


def disconnect(topic):
    integrations = ray.get(topic._disconnect.remote())
    for i in integrations:
        i['integration'].cancel()
