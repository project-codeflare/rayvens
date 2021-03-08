import atexit
import collections
import ray
import requests

from .impl import Camel


@ray.remote(num_cpus=0)
class Topic:
    def __init__(self, name):
        self.name = name
        self._subscribers = []
        self._integrations = []
        self._callable = None

    def subscribe(self, callable, name=None):
        self._subscribers.append({'callable': callable, 'name': name})

    def publish(self, data):
        if data is None:
            return
        if self._callable is not None:
            data = self._callable(data)
        for s in self._subscribers:
            s['callable'](data)

    def add_operator(self, callable):
        self._callable = callable

    def _register(self, name, integration):
        self._integrations.append({'name': name, 'integration': integration})

    def _disconnect(self, camel):
        self._subscribers = []
        camel.cancel.remote(self._integrations)
        self._integrations = []

    def _post(self, url, data):
        if data is not None:
            requests.post(url, data)


class _Remote:
    def __init__(self, name, make):
        self._name = name
        self.remote = make

    def __call__(self, *args, **kwargs):
        raise TypeError(
            "Actors cannot be instantiated directly. "
            f"Instead of '{self._name}()', use '{self._name}.remote()'.")


class Client:
    def __init__(self):
        self._camel = Camel.start()
        atexit.register(self._camel.exit.remote)
        self.Topic = Topic
        self.Source = _Remote('Source', self._Source)
        self.Sink = _Remote('Sink', self._Sink)
        self.Operator = _Remote('Operator', self._Operator)

    def add_source(self, name, topic, *args, **kwargs):
        self._camel.add_source.remote(name, topic, *args, **kwargs)

    def _Source(self, name, *args, **kwargs):
        topic = Topic.remote(name)
        self.add_source(name, topic, *args, **kwargs)
        return topic

    def add_sink(self, name, topic, *args, **kwargs):
        self._camel.add_sink.remote(name, topic, *args, **kwargs)

    def _Sink(self, name, *args, **kwargs):
        topic = Topic.remote(name)
        self.add_sink(name, topic, *args, **kwargs)
        return topic

    def _Operator(self, name, callable):
        topic = Topic.remote(name)
        topic.add_operator.remote(callable)
        return topic

    def disconnect(self, topic):
        topic._disconnect.remote(self._camel)
