import ray

from rayvens.core.impl import start as start_mode_1
from rayvens.core.camel_anywhere.impl import start as start_mode_2


@ray.remote(num_cpus=0)
class Topic:
    def __init__(self, name):
        self.name = name
        self._subscribers = []
        self._operator = None

    def send_to(self, subscriber, name=None):
        self._subscribers.append({'subscriber': subscriber, 'name': name})

    def ingest(self, data):
        if data is None:
            return
        if self._operator is not None:
            data = _eval(self._operator, data)
        for s in self._subscribers:
            _eval(s['subscriber'], data)

    def add_operator(self, operator):
        self._operator = operator


def _eval(f, data):
    if isinstance(f, ray.actor.ActorHandle):
        return f.ingest.remote(data)
    elif isinstance(f, ray.actor.ActorMethod) or isinstance(
            f, ray.remote_function.RemoteFunction):
        return f.remote(data)
    else:
        return f(data)


def _rshift(topic, subscriber):
    topic.send_to.remote(subscriber)
    return subscriber


def _lshift(topic, data):
    topic.ingest.remote(data)
    return topic


setattr(ray.actor.ActorHandle, '__rshift__', _rshift)
setattr(ray.actor.ActorHandle, '__lshift__', _lshift)


def _start(camel_mode):
    if camel_mode in ['local', 'operator1']:
        return start_mode_1
    elif camel_mode == 'auto':
        return start_mode_1  # TODO
    elif camel_mode in [
            'anywhere.local', 'anywhere.mixed', 'anywhere.operator1'
    ]:
        return start_mode_2
    else:
        raise TypeError(
            'Unsupported camel_mode. Must be one of auto, local, operator1.')


class Client:
    def __init__(self, prefix='/rayvens', camel_mode='auto'):
        self._camel = _start(camel_mode)(prefix, camel_mode)

    def create_topic(self, name, source=None, sink=None, operator=None):
        topic = Topic.remote(name)
        if source is not None:
            self.add_source(name, topic, source)
        if sink is not None:
            self.add_sink(name, topic, sink)
        if operator is not None:
            topic.add_operator.remote(operator)
        return topic

    def add_source(self, name, topic, source):
        self._camel.add_source.remote(name, topic, source)

    def add_sink(self, name, topic, sink):
        self._camel.add_sink.remote(name, topic, sink)
