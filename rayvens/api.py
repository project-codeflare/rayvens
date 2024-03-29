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
import time

from rayvens.core.local import start as start_http
from rayvens.core.kafka import start as start_kafka
from rayvens.core.operator import start as start_operator_http
from rayvens.core.operator_kafka import start as start_operator_kafka
from rayvens.core.ray_serve import start as start_operator_ray_serve
from rayvens.core.name import name_source, name_sink
from rayvens.core.verify import verify_do
from queue import Queue


class Stream:
    def __init__(self,
                 name,
                 actor_options={},
                 operator=None,
                 source_config=None,
                 sink_config=None,
                 batch_size=None):
        if _global_camel is None:
            raise RuntimeError(
                "Rayvens has not been started. Start with 'rayvens.init()'.")
        self.name = name
        self.actor = StreamActor.options(*actor_options).remote(
            name, operator=operator, batch_size=batch_size)
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

    def add_operator(self, operator, batch_size=None):
        return ray.get(self.actor.add_operator.remote(operator, batch_size))

    def add_multitask_operator(self, operator, batch_size=None):
        return ray.get(
            self.actor.add_multitask_operator.remote(operator, batch_size))

    def add_source(self, source_config):
        return ray.get(self.actor.add_source.remote(self, source_config))

    def add_sink(self, sink_config):
        return ray.get(self.actor.add_sink.remote(self, sink_config))

    def unsubscribe(self, subscriber_name):
        return ray.get(self.actor.unsubscribe.remote(subscriber_name))

    def disconnect_source(self, source_name, after_idle_for=None, after=None):
        self._wait_for_timeout(after_idle_for)
        return ray.get(self.actor.disconnect_source.remote(source_name))

    def disconnect_sink(self, sink_name, after_idle_for=None, after=None):
        self._wait_for_timeout(after_idle_for)
        return ray.get(self.actor.disconnect_sink.remote(sink_name))

    def disconnect_all(self,
                       after_idle_for=None,
                       after=None,
                       stream_drain_timeout=5):
        self._wait_for_timeout(after_idle_for, after)
        return ray.get(self.actor.disconnect_all.remote(stream_drain_timeout))

    def event_count(self):
        return ray.get(self.actor.event_count.remote())

    def _meta(self, action, *args, **kwargs):
        return ray.get(self.actor._meta.remote(action, *args, **kwargs))

    def _wait_for_timeout(self, after_idle_for, after):
        if after_idle_for is not None and after_idle_for > 0:
            while True:
                time_elapsed_since_last_event = self._idle_time()

                if time_elapsed_since_last_event is not None:
                    # Idle timeout exceeds the user-specified time limit:
                    if time_elapsed_since_last_event > after_idle_for:
                        break

                    # Check again after waiting for the rest of the timeout
                    # time:
                    time.sleep(after_idle_for - time_elapsed_since_last_event +
                               1)
                else:
                    time.sleep(after_idle_for)
        if after is not None and after > 0:
            time.sleep(after)

    def _idle_time(self):
        latest_timestamp = ray.get(self.actor._get_latest_timestamp.remote())
        if latest_timestamp is None:
            return None
        return time.time() - latest_timestamp


class StreamContext:
    def __init__(self, stream_batch_size):
        self.sink_restrictions = {}
        self.subscribers = {}
        self.latest_sent_event_timestamp = None
        self.event_counter = 0
        self.limit_subscribers = False
        self.is_multi_operator = False
        self.stream_batch_size = stream_batch_size

    def publish(self, data):
        if data is not None:
            for name, subscriber in self.subscribers.items():
                if name in self.sink_restrictions:
                    type_restrictions = self.sink_restrictions[name]
                    if not self._accepts_data_type(data, type_restrictions):
                        continue
                _eval(self, subscriber, data)

    # Check if the sink we are routing the message to has any restrictions
    # in terms of message type. A message will only be routed to a sink
    # if the sink accepts its type.
    def _accepts_data_type(self, data, type_restrictions):
        # If there are no restrictions return immediately:
        if len(type_restrictions) == 0:
            return True
        for restricted_type in type_restrictions:
            if isinstance(data, restricted_type):
                return True
        return False


@ray.remote(num_cpus=0)
class StreamActor:
    def __init__(self, name, operator=None, batch_size=None):
        self.name = name
        self._operator = operator
        self._sources = {}
        self._sinks = {}
        self.context = StreamContext(batch_size)
        self.queue = None
        if self.context.stream_batch_size is not None:
            self.queue = Queue(maxsize=self.context.stream_batch_size)

    def send_to(self, subscriber, name=None):
        if self.context.limit_subscribers:
            return
        if name in self.context.subscribers:
            raise RuntimeError(
                f'Stream {self.name} already has a subscriber named {name}.')
        if name is None:
            name = object()
        self.context.subscribers[name] = subscriber

    def append(self, data):
        if data is None:
            return
        if self.queue is not None:
            self.queue.put_nowait(data)
            if not self.queue.full():
                return
            data = list(self.queue.queue)
            with self.queue.mutex:
                self.queue.queue.clear()
        if self._operator is not None:
            data = _eval(self.context, self._operator, data)
        self.context.publish(data)
        self.context.latest_sent_event_timestamp = time.time()
        self.context.event_counter += 1

    def add_operator(self, operator, batch_size):
        self._operator = operator
        self.context.batch_size = batch_size

    def add_multitask_operator(self, operator, batch_size):
        self._operator = operator
        self.context.batch_size = batch_size
        self.context.is_multi_operator = True

    def add_source(self, stream, source_config):
        source_config["integration_type"] = 'source'
        source_name = name_source(source_config)
        if source_name in self._sources:
            raise RuntimeError(
                f'Stream {self.name} already has a source named {source_name}.'
            )
        self._sources[source_name] = _global_camel.add_source(
            stream, source_config, source_name)
        return source_name

    def add_sink(self, stream, sink_config):
        sink_config["integration_type"] = 'sink'
        sink_name = name_sink(sink_config)
        if sink_name in self._sinks:
            raise RuntimeError(
                f'Stream {self.name} already has a sink named {sink_name}.')
        self._sinks[sink_name] = _global_camel.add_sink(
            stream, sink_config, sink_name)
        self.context.sink_restrictions[sink_name] = self._sinks[
            sink_name].get_restricted_data_type()
        return sink_name

    def unsubscribe(self, subscriber_name):
        if subscriber_name not in self._subscribers:
            raise RuntimeError(f'Stream {self.name} has no subscriber named'
                               f' {subscriber_name}.')
        self.context.subscribers.pop(subscriber_name)

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
        self.context.sink_restrictions.pop(sink_name)
        self.context.subscribers.pop(sink_name)

    def disconnect_all(self, stream_drain_timeout):
        for source_name in dict(self._sources):
            self.disconnect_source(source_name)
        if self.queue is not None:
            self.flush_batch()
        time.sleep(stream_drain_timeout)
        for sink_name in dict(self._sinks):
            self.disconnect_sink(sink_name)

    def event_count(self):
        return self.context.event_counter

    def flush_batch(self):
        data = None
        if self.queue is not None:
            data = list(self.queue.queue)
            with self.queue.mutex:
                self.queue.queue.clear()
        if data is None:
            return
        if self._operator is not None:
            data = _eval(self.context, self._operator, data)
        self.context.publish(data)
        self.context.latest_sent_event_timestamp = time.time()
        self.context.event_counter += 1

    def _get_integration(self, source_sink_name):
        if source_sink_name in self._sinks:
            integration = self._sinks[source_sink_name]
        if source_sink_name in self._sources:
            integration = self._sources[source_sink_name]
        if integration is None:
            raise RuntimeError(
                f'{source_sink_name} not found on stream {self.name}')
        return integration

    def _integration_invoke(self, source_sink_name, message):
        integration = self._get_integration(source_sink_name)
        return integration.invocation.invoke(message)

    def _get_integration_name(self, source_sink_name):
        return self._get_integration(source_sink_name).integration_name

    def _get_latest_timestamp(self):
        return self.context.latest_sent_event_timestamp

    def _fetch_processors(self):
        self.context.limit_subscribers = True
        return self.context.subscribers, self._operator

    def _update_timestamp(self, timestamp):
        self.context.latest_sent_event_timestamp = timestamp


def _eval(context, f, data):
    if isinstance(f, Stream):
        return f.append(data)
    elif isinstance(f, ray.actor.ActorHandle):
        return f.append.remote(data)
    elif isinstance(f, ray.actor.ActorMethod):
        return f.remote(data)
    elif isinstance(f, ray.remote_function.RemoteFunction):
        if context.is_multi_operator:
            if context.subscribers is None:
                raise RuntimeError('No subscribers or sinks provided.')
            f.remote(context, data)
            return None
        return f.remote(data)
    else:
        return f(data)


setattr(Stream, '__rshift__', Stream.send_to)
setattr(Stream, '__lshift__', Stream.append)

_global_camel = None


def init(mode=os.getenv('RAYVENS_MODE', 'auto'),
         transport=os.getenv('RAYVENS_TRANSPORT', 'auto'),
         release=os.getenv('RAYVENS_RELEASE', False),
         check_port=True):
    modes = ['auto', 'local', 'mixed', 'operator']
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
            _global_camel = start_http(mode, check_port, release)
        elif transport == 'kafka':
            _global_camel = start_kafka(mode, check_port, release)
        else:
            raise RuntimeError(
                f'{transport} transport unsupported for mode {mode}.')
    elif mode in ['mixed', 'operator']:
        if transport in ['auto', 'http']:
            _global_camel = start_operator_http(mode, check_port, release)
        elif transport == 'kafka':
            _global_camel = start_operator_kafka(mode, check_port, release)
        elif transport in ['ray-serve']:
            _global_camel = start_operator_ray_serve(mode, check_port, release)
        else:
            raise RuntimeError(
                f'{transport} transport unsupported for mode {mode}.')
    else:
        raise RuntimeError(f'Unsupported mode {mode}.')


def meta(stream, action, *args, **kwargs):
    return verify_do(stream.actor, _global_camel, action, *args, **kwargs)
