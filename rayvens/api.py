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
        ray.wait(
            [self.actor._init.remote(self.actor, source_config, sink_config)])

    def send_to(self, subscriber, name=None):
        if (isinstance(subscriber, ray.actor.ActorHandle)) and getattr(
                subscriber, 'send_to', None) is None:
            subscriber = Stream('implicit', operator=subscriber)
        ray.wait([self.actor.send_to.remote(subscriber, name)])
        return subscriber

    def append(self, data):
        self.actor.append.remote(data)
        return self

    def add_operator(self, operator):
        ray.wait([self.actor.add_operator.remote(operator)])

    def add_source(self, source_config):
        return ray.get(self.actor.add_source.remote(source_config))

    def add_sink(self, sink_config):
        return ray.get(self.actor.add_sink.remote(sink_config))

    def disconnect(self, integration):
        ray.get(self.actor.disconnect.remote(integration))

    def disconnect_all(self):
        ray.get(self.actor.disconnect_all.remote())


@ray.remote(num_cpus=0)
class StreamActor:
    def __init__(self, name, operator=None):
        self.name = name
        self._subscribers = []
        self._operator = operator
        self._sources = []
        self._sinks = []

    def _init(self, handle, source_config, sink_config):
        self._handle = handle
        if sink_config is not None:
            self.add_sink(sink_config)
        if source_config is not None:
            self.add_source(source_config)

    def send_to(self, subscriber, name=None):
        # TODO: make name mandatory and use it to remove subscribers.
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

    def add_source(self, source_config):
        source = _global_camel.add_source(self, source_config, self._handle)
        self._sources.append(source)
        return source

    def add_sink(self, sink_config):
        sink = _global_camel.add_sink(self, sink_config, self._handle)
        self._sinks.append(sink)
        return sink

    def disconnect(self, integration):
        is_sink = integration in self._sinks
        is_source = integration in self._sources

        if not is_sink and not is_source:
            raise RuntimeError(f'{integration} is not a valid source or sink')

        success = _global_camel.disconnect(integration)
        # TODO: remove subscribers
        if success:
            if is_source:
                self._sources.remove(integration)
            else:
                self._sinks.remove(integration)

    def disconnect_all(self):
        success = _global_camel.disconnect_all()
        # TODO: remove subscribers
        if success:
            self._subscribers = []
            self._sources = []
            self._sinks = []


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
    modes = ['auto', 'local', 'mixed.operator', 'cluster.operator']
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
