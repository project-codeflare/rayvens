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

import atexit
import os
import ray
import signal
import subprocess
import yaml
from confluent_kafka import Consumer, Producer
import threading
from rayvens.core.validation import Validation
import rayvens.core.catalog as catalog

integrations = []


def killall():
    global integrations
    for integration in integrations:
        integration.cancel()


# instantiate camel actor manager and setup exit hook
def start(prefix, mode):
    camel = Camel(mode)
    atexit.register(camel.killall)
    return camel


class Camel:
    def __init__(self, mode):
        self.streams = []
        self.mode = mode
        self.validation = Validation()

    def add_stream(self, stream, name):
        self.validation.add_stream(stream, name)

    def add_source(self, stream, config):
        # Get stream name.
        name = self.validation.get_stream_name(stream)

        self.streams.append(stream)
        spec = catalog.construct_source(config,
                                        f'kafka:{name}?brokers=${brokers()}')

        def run():
            integration = Integration(name, spec)
            integration.send_to(stream)

        stream._exec.remote(run)

    def add_sink(self, stream, config):
        # Get stream name.
        name = self.validation.get_stream_name(stream)

        self.streams.append(stream)
        spec = catalog.construct_sink(config,
                                      f'kafka:{name}?brokers=${brokers()}')

        def run():
            integration = Integration(name, spec)
            integration.recv_from(stream)

        stream._exec.remote(run)

    def await_start(self, integration_name):
        return True

    def await_start_all(self, stream):
        return True

    def killall(self):
        for stream in self.streams:
            stream._exec.remote(killall)


# the low-level implementation-specific stuff


@ray.remote(num_cpus=0)
class ProducerActor:
    def __init__(self, name):
        self.producer = ProducerHelper(name)

    def append(self, data):
        self.producer.produce(data)


class ProducerHelper:
    def __init__(self, name):
        self.name = name
        self.producer = Producer({'bootstrap.servers': brokers()})

    def produce(self, data):
        if data is not None:
            self.producer.produce(self.name, data.encode('utf-8'))


def brokers():
    host = os.getenv('KAFKA_SERVICE_HOST', 'localhost')
    port = os.getenv('KAFKA_SERVICE_PORT', '31093')
    return f'{host}:{port}'


class Integration:
    def __init__(self, name, spec):
        self.name = name
        filename = f'{name}.yaml'
        with open(filename, 'w') as f:
            yaml.dump(spec, f)
        command = ['kamel', 'local', 'run', filename]
        process = subprocess.Popen(command, start_new_session=True)
        self.pid = process.pid
        global integrations
        integrations.append(self)

    def send_to(self, stream):
        # use kafka consumer thread to push from camel source to rayvens stream
        consumer = Consumer({
            'bootstrap.servers': brokers(),
            'group.id': 'ray',
            'auto.offset.reset': 'latest'
        })

        consumer.subscribe([self.name])

        def append():
            while True:
                msg = consumer.poll()
                if msg.error():
                    print(f'consumer error: ${msg.error()}')
                else:
                    stream.append.remote(msg.value().decode('utf-8'))

        threading.Thread(target=append).start()

    def recv_from(self, stream):
        # use kafka producer actor to push from rayvens stream to camel sink
        helper = ProducerActor.remote(self.name)
        stream.send_to.remote(helper, self.name)

    def cancel(self):
        try:
            os.killpg(os.getpgid(self.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
