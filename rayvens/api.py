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
    if camel_mode in ['kafka']:
        return start_mode_kafka
    elif camel_mode in ['auto']:
        return start_mode_http
    elif camel_mode in ['local', 'mixed.operator', 'cluster.operator']:
        return start_mode_2
    else:
        raise TypeError('Unsupported camel_mode.')


class Client:
    def __init__(self,
                 prefix='/rayvens',
                 camel_mode=os.getenv('RAYVENS_MODE', 'auto')):
        self._camel = _start(camel_mode)(prefix, camel_mode)

    # Create a new stream.
    def create_stream(self, name, source=None, sink=None, operator=None):
        stream = Stream.remote(name, operator=operator)
        self._camel.add_stream(stream, name)
        if source is not None:
            self.add_source(stream, source)
        if sink is not None:
            self.add_sink(stream, sink)
        return stream

    # Attach source to stream.
    def add_source(self, stream, source):
        return self._camel.add_source(stream, source)

    # Attach sink to stream.
    def add_sink(self, stream, sink):
        return self._camel.add_sink(stream, sink)

    # Wait for a particular integration to start.
    def await_start(self, integration_name):
        successful_await = self._camel.await_start(integration_name)
        if not successful_await:
            raise RuntimeError('await_start command failed.')

    # Wait for all integrations attached to a particular Stream to start.
    def await_start_all(self, stream):
        successful_await = self._camel.await_start_all(stream)
        if not successful_await:
            raise RuntimeError('await_start_all command failed.')
