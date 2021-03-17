import os
import ray

from rayvens.core.impl import start as start_mode_1
from rayvens.core.camel_anywhere.impl import start as start_mode_2


@ray.remote(num_cpus=0)
class Stream:
    def __init__(self, name, operator=None):
        self.name = name
        self._subscribers = []
        self._operator = operator

    def send_to(self, subscriber, name=None):
        self._subscribers.append({'subscriber': subscriber, 'name': name})

    def append(self, data):
        if data is None:
            return
        if self._operator is not None:
            data = _eval(self._operator, data)
        for s in self._subscribers:
            _eval(s['subscriber'], data)

    def add_operator(self, operator):
        self._operator = operator

    def _exec(self, f, *args):
        return f(*args)


def _eval(f, data):
    if isinstance(f, ray.actor.ActorHandle):
        return f.append.remote(data)
    elif isinstance(f, ray.actor.ActorMethod) or isinstance(
            f, ray.remote_function.RemoteFunction):
        return f.remote(data)
    else:
        return f(data)


def _rshift(stream, subscriber):
    if (not isinstance(subscriber, ray.actor.ActorHandle)) or getattr(
            subscriber, 'send_to', None) is None:
        # wrap subscriber with stream
        subscriber = Stream.remote('implicit', operator=subscriber)
    stream.send_to.remote(subscriber)
    return subscriber


def _lshift(stream, data):
    stream.append.remote(data)
    return stream


setattr(ray.actor.ActorHandle, '__rshift__', _rshift)
setattr(ray.actor.ActorHandle, '__lshift__', _lshift)


def _start(camel_mode):
    if camel_mode in ['pack', 'spread']:
        return start_mode_1
    elif camel_mode == 'auto':
        return start_mode_1  # TODO
    elif camel_mode in ['local', 'mixed', 'operator']:
        return start_mode_2
    else:
        raise TypeError('Unsupported camel_mode.')


class Client:
    def __init__(self,
                 prefix='/rayvens',
                 camel_mode=os.getenv('RAYVENS_MODE', 'auto')):
        self._camel = _start(camel_mode)(prefix, camel_mode)

    def create_stream(self, name, source=None, sink=None, operator=None):
        stream = Stream.remote(name, operator=operator)
        if source is not None:
            self.add_source(name, stream, source)
        if sink is not None:
            self.add_sink(name, stream, sink)
        return stream

    def add_source(self, name, stream, source):
        self._camel.add_source.remote(name, stream, source)

    def add_sink(self, name, stream, sink):
        self._camel.add_sink.remote(name, stream, sink)
