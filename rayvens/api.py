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

from rayvens.core.local import Camel as start_http
from rayvens.core.kafka import Camel as start_kafka
from rayvens.core.operator import start as start_operator


class Stream:
    def __init__(self,
                 name,
                 actor_options=None,
                 operator=None,
                 source_config=None,
                 sink_config=None):
        if _global_camel is None:
            raise RuntimeError(
                "Rayvens has not been started. Start with 'rayvens.init()'.")
        self.name = name
        self.actor = StreamActor.options(actor_options).remote(
            name, operator=operator)
        if sink_config is not None:
            self.add_sink(sink_config)
        if source_config is not None:
            self.add_source(source_config)

    def send_to(self, subscriber, name=None):
        if (isinstance(subscriber, ray.actor.ActorHandle)) and getattr(
                subscriber, 'send_to', None) is None:
            subscriber = Stream('implicit', operator=subscriber)
        ray.get(self.actor.send_to.remote(subscriber, name))
        return subscriber

    def append(self, data):
        self.actor.append.remote(data)
        return self

    def add_operator(self, operator):
        ray.get(self.actor.add_operator.remote(operator))

    def add_source(self, source_config):
        return ray.get(self.actor.add_source.remote(self, source_config))

    def add_sink(self, sink_config):
        return ray.get(self.actor.add_sink.remote(self, sink_config))

    def disconnect_source(self, source_name):
        return ray.get(self.actor.disconnect_source.remote(source_name))

    def disconnect_sink(self, sink_name):
        return ray.get(self.actor.disconnect.remote(sink_name))

    def disconnect_all(self):
        return ray.get(self.actor.disconnect_all.remote())


@ray.remote(num_cpus=0)
class StreamActor:
    def __init__(self, name, operator=None):
        self.name = name
        self._subscribers = {}
        self._operator = operator
        self._sources = []
        self._sinks = []

    def send_to(self, subscriber, name=None):
        if name is None:
            name = object()
        if name in self._subscribers:
            raise RuntimeError(
                f'Stream {self.name} already has a subscriber named {name}.')
        self._subscribers[name] = subscriber

    def append(self, data):
        if data is None:
            return
        if self._operator is not None:
            data = _eval(self._operator, data)
        for subscriber in self._subscribers.values():
            _eval(subscriber, data)

    def add_operator(self, operator):
        self._operator = operator

    def add_source(self, stream, source_config):
        source = _global_camel.add_source(stream, source_config)
        self._sources.append(source)
        return source

    def add_sink(self, stream, sink_config):
        sink = _global_camel.add_sink(stream, sink_config)
        self._sinks.append(sink)
        return sink

    def disconnect_source(self, source_name):
        if source_name not in self._sources:
            raise RuntimeError(
                f'Stream {self.name} has no source {source_name}.')
        self._sources.remove(source_name)
        return _global_camel.disconnect(source_name)

    def disconnect_sink(self, sink_name):
        if sink_name not in self._sinks:
            raise RuntimeError(f'Stream {self.name} has no sink {sink_name}.')
        self._sinks.remove(sink_name)
        self._subscribers.pop(sink_name)
        return _global_camel.disconnect(sink_name)

    def disconnect_all(self):
        self._subscribers = []
        self._sources = []
        self._sinks = []
        return _global_camel.disconnect_all()


def _eval(f, data):
    if isinstance(f, Stream):
        return f.append(data)
    elif isinstance(f, ray.actor.ActorHandle):
        return f.append.remote(data)
    elif isinstance(f, ray.actor.ActorMethod) or isinstance(
            f, ray.remote_function.RemoteFunction):
        return f.remote(data)
    else:
        return f(data)


setattr(Stream, '__rshift__', Stream.send_to)
setattr(Stream, '__lshift__', Stream.append)

_global_camel = None


def init(mode=os.getenv('RAYVENS_MODE', 'auto'),
         transport=os.getenv('RAYVENS_TRANSPORT', 'auto')):
    modes = [
        'auto', 'local', 'local.local', 'mixed.operator', 'cluster.operator'
    ]
    transports = ['auto', 'http', 'kafka']

    if mode not in modes:
        raise RuntimeError(
            f'Unsupported Rayvens mode. Must be one of {modes}.')
    if transport not in transports:
        raise RuntimeError(
            f'Unsupported Rayvens transport. Must be one of {transports}.')

    global _global_camel

    if mode in ['auto', 'local']:
        if transport in ['auto', 'http']:
            _global_camel = start_http()
        else:
            _global_camel = start_kafka()
    else:
        _global_camel = start_operator(mode)
