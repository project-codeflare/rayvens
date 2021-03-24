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

import os
import ray

from rayvens.core.impl import start as start_mode_http
from rayvens.core.kafka import start as start_mode_kafka
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

    def add_source(self, source):
        return _global_camel.add_source(self, source, self._handle)

    def add_sink(self, sink):
        return _global_camel.add_sink(self, sink, self._handle)

    def await_start_all(self):
        successful_await = _global_camel.await_start_all(self._handle)
        if not successful_await:
            raise RuntimeError('await_start_all command failed.')

    def _exec(self, f, *args):
        return f(*args)

    def _set(self, handle):
        _global_camel.add_stream(handle, self.name)
        self._handle = handle


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
        subscriber = create_stream('implicit', operator=subscriber)
    stream.send_to.remote(subscriber)
    return subscriber


def _lshift(stream, data):
    stream.append.remote(data)
    return stream


setattr(ray.actor.ActorHandle, '__rshift__', _rshift)
setattr(ray.actor.ActorHandle, '__lshift__', _lshift)

_global_camel = None


def init(mode=os.getenv('RAYVENS_MODE', 'auto')):
    global _global_camel
    if mode in ['kafka']:
        _global_camel = start_mode_kafka(mode)
    elif mode in ['auto']:
        _global_camel = start_mode_http(mode)
    elif mode in ['local', 'mixed.operator', 'cluster.operator']:
        _global_camel = start_mode_2(mode)
    else:
        raise TypeError('Unsupported mode.')


# Create a new stream.
def create_stream(name,
                  actor_options=None,
                  source=None,
                  sink=None,
                  operator=None):
    if _global_camel is None:
        raise TypeError('Rayvens has not been started.')
    stream = Stream.options(actor_options).remote(name, operator=operator)
    stream._set.remote(stream)
    if source is not None:
        stream.add_source.remote(source)
    if sink is not None:
        stream.add_sink.remote(sink)
    return stream
