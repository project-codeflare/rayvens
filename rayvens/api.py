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

from rayvens.core.local import start as start_http
from rayvens.core.kafka import start as start_kafka
from rayvens.core.operator import start as start_operator_http
from rayvens.core.ray_serve import start as start_operator_ray_serve
from rayvens.core.name import name_source, name_sink
from rayvens.core.verify import verify_do


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
        ray.get(self.actor.send_to.remote(subscriber, name))
        return subscriber

    def append(self, data):
        self.actor.append.remote(data)
        return self

    def add_operator(self, operator):
        return ray.get(self.actor.add_operator.remote(operator))

    def add_source(self, source_config):
        return ray.get(self.actor.add_source.remote(self, source_config))

    def add_sink(self, sink_config):
        return ray.get(self.actor.add_sink.remote(self, sink_config))

    def unsubscribe(self, subscriber_name):
        return ray.get(self.actor.unsubscribe.remote(subscriber_name))

    def disconnect_source(self, source_name):
        return ray.get(self.actor.disconnect_source.remote(source_name))

    def disconnect_sink(self, sink_name):
        return ray.get(self.actor.disconnect_sink.remote(sink_name))

    def disconnect_all(self):
        return ray.get(self.actor.disconnect_all.remote())

    def _meta(self, action, *args, **kwargs):
        return ray.get(self.actor._meta.remote(action, *args, **kwargs))


@ray.remote(num_cpus=0)
class StreamActor:
    def __init__(self, name, operator=None):
        self.name = name
        self._subscribers = {}
        self._operator = operator
        self._sources = {}
        self._sinks = {}

    def send_to(self, subscriber, name=None):
        if name in self._subscribers:
            raise RuntimeError(
                f'Stream {self.name} already has a subscriber named {name}.')
        if name is None:
            name = object()
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
        source_name = name_source(source_config)
        if source_name in self._sources:
            raise RuntimeError(
                f'Stream {self.name} already has a source named {source_name}.'
            )
        self._sources[source_name] = _global_camel.add_source(
            stream, source_config, source_name)
        return source_name

    def add_sink(self, stream, sink_config):
        sink_name = name_sink(sink_config)
        if sink_name in self._sinks:
            raise RuntimeError(
                f'Stream {self.name} already has a sink named {sink_name}.')
        self._sinks[sink_name] = _global_camel.add_sink(
            stream, sink_config, sink_name)
        return sink_name

    def unsubscribe(self, subscriber_name):
        if subscriber_name not in self._subscribers:
            raise RuntimeError(
                f'Stream {self.name} has no subscriber named {subscriber_name}.'
            )
        self._subscribers.pop(subscriber_name)

    def disconnect_source(self, source_name):
        if source_name not in self._sources:
            raise RuntimeError(
                f'Stream {self.name} has no source named {source_name}.')
        _global_camel.disconnect(self._sources[source_name])
        self._sources.pop(source_name)

    def disconnect_sink(self, sink_name):
        if sink_name not in self._sinks:
            raise RuntimeError(
                f'Stream {self.name} has no sink named {sink_name}.')
        _global_camel.disconnect(self._sinks[sink_name])
        self._sinks.pop(sink_name)
        self._subscribers.pop(sink_name)

    def disconnect_all(self):
        for source_name in dict(self._sources):
            self.disconnect_source(source_name)
        for sink_name in dict(self._sinks):
            self.disconnect_sink(sink_name)

    def _meta(self, action, *args, **kwargs):
        return verify_do(self, _global_camel, action, *args, **kwargs)


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
    modes = ['auto', 'local', 'mixed.operator', 'operator']
    transports = ['auto', 'http', 'kafka', 'ray-serve']

    if mode not in modes:
        raise RuntimeError(
            f'Unsupported Rayvens mode. Must be one of {modes}.')
    if transport not in transports:
        raise RuntimeError(
            f'Unsupported Rayvens transport. Must be one of {transports}.')

    global _global_camel

    if mode in ['auto', 'local']:
        if transport in ['auto', 'http']:
            _global_camel = start_http(mode)
        elif transport == 'kafka':
            _global_camel = start_kafka(mode)
        else:
            raise RuntimeError(
                f'{transport} transport unsupported for mode {mode}.')
    elif mode in ['mixed.operator', 'operator']:
        if transport in ['auto', 'http']:
            _global_camel = start_operator_http(mode)
        elif transport in ['ray-serve']:
            _global_camel = start_operator_ray_serve(mode)
        else:
            raise RuntimeError(
                f'{transport} transport unsupported for mode {mode}.')
    else:
        raise RuntimeError(f'Unsupported mode {mode}.')
