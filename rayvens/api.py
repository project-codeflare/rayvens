import atexit
import ray

from .impl import Camel


@ray.remote(num_cpus=0)
class Topic:
    def __init__(self, name):
        self.name = name
        self._subscribers = []
        self._integrations = []

    def subscribe(self, callable, name=None):
        self._subscribers.append({'callable': callable, 'name': name})

    def publish(self, *args, **kwargs):
        for s in self._subscribers:
            s['callable'](*args, **kwargs)

    def _register(self, name, integration):
        self._integrations.append({'name': name, 'integration': integration})

    def _disconnect(self, camel):
        self._subscribers = []
        camel.cancel.remote(self._integrations)
        self._integrations = []


class Client:
    def __init__(self):
        self._camel = Camel.start()
        atexit.register(self._camel.exit.remote)

    def Topic(self, name):
        return Topic.remote(name)

    def add_source(self, name, *args, **kwargs):
        self._camel.add_source.remote(name, *args, **kwargs)

    def Source(self, name, *args, **kwargs):
        topic = Topic.remote(name)
        self.add_source(name, topic, *args, **kwargs)
        return topic

    def add_sink(self, name, *args, **kwargs):
        self._camel.add_sink.remote(name, *args, **kwargs)

    def Sink(self, name, *args, **kwargs):
        topic = Topic.remote(name)
        self.add_sink(name, topic, *args, **kwargs)
        return topic

    def disconnect(self, topic):
        topic._disconnect.remote(self._camel)
