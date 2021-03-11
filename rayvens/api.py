import atexit
import ray
import requests

from rayvens.core.impl import Camel
from rayvens.core.camel_anywhere.impl import CamelAnyNode
from rayvens.types import CamelOperatorMode


@ray.remote(num_cpus=0)
class Topic:
    def __init__(self, name):
        self.name = name
        self._subscribers = []
        self._integrations = []
        self._endpoint_calls = []
        self._callable = None

    def send_to(self, callable, name=None):
        self._subscribers.append({'callable': callable, 'name': name})

    def ingest(self, data):
        if data is None:
            return
        if self._callable is not None:
            data = self._callable(data)
        for s in self._subscribers:
            s['callable'](data)
        for endpoint_call in self._endpoint_calls:
            endpoint_call['callable'].remote(endpoint_call['endpoint_name'],
                                             data)

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

    def _save_endpoint_call(self, callable, endpoint_name):
        self._endpoint_calls.append({
            'callable': callable,
            'endpoint_name': endpoint_name
        })


def _remote(x):
    if isinstance(x, ray.actor.ActorHandle):
        return x.ingest.remote
    elif isinstance(x, ray.actor.ActorMethod) or isinstance(
            x, ray.remote_function.RemoteFunction):
        return x.remote
    else:
        return x


def _rshift(source, sink):
    source.send_to.remote(_remote(sink))
    return sink


def _lshift(topic, data):
    topic.ingest.remote(data)
    return topic


setattr(ray.actor.ActorHandle, '__rshift__', _rshift)
setattr(ray.actor.ActorHandle, '__lshift__', _lshift)


class Client:
    def __init__(self,
                 prefix='/rayvens',
                 camel_operator_mode=CamelOperatorMode.HEAD_NODE):
        self.camel_operator_mode = camel_operator_mode
        if self.camel_operator_mode == CamelOperatorMode.HEAD_NODE:
            self._camel = Camel.start(prefix)
        elif self.camel_operator_mode == CamelOperatorMode.ANY_NODE:
            self._camel = CamelAnyNode.start(prefix)
            self._camel.start_kamel_backend.remote()
        else:
            raise RuntimeError("Not yet implemented")
        atexit.register(self._camel.exit.remote)

    def create_topic(self, name, source=None, sink=None, operator=None):
        topic = Topic.remote(name)
        if source is not None:
            self.add_source(name, topic, source)
        if sink is not None:
            self.add_sink(name, topic, sink)
        if operator is not None:
            topic.add_operator.remote(_remote(operator))
        return topic

    def add_source(self, name, topic, source):
        self._camel.add_source.remote(name, topic, source)

    def add_sink(self, name, topic, sink):
        self._camel.add_sink.remote(name, topic, sink)

    def disconnect(self, topic):
        if self.camel_operator_mode == CamelOperatorMode.ANY_NODE:
            # TODO:
            # self._camel.stop_kamel_backend.remote()
            self._camel.exit.remote()
        else:
            topic._disconnect.remote(self._camel)
