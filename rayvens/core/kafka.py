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
import signal
import subprocess
import yaml
from confluent_kafka import Consumer, Producer
import threading
import rayvens.core.catalog as catalog
import sys


class Camel:
    def add_source(self, stream, config):
        spec = catalog.construct_source(
            config, f'kafka:{stream.name}?brokers={brokers()}')
        integration = Integration(stream.name, spec)
        integration.send_to(stream.actor)

    def add_sink(self, stream, config):
        spec = catalog.construct_sink(
            config, f'kafka:{stream.name}?brokers={brokers()}')
        integration = Integration(stream.name, spec)
        integration.recv_from(stream.actor)


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
        harness = os.path.join(os.path.dirname(__file__), 'harness.py')
        command = [sys.executable, harness, 'kamel', 'local', 'run', filename]
        process = subprocess.Popen(command, start_new_session=True)
        self.pid = process.pid

    def send_to(self, handle):
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
                    print(f'consumer error: {msg.error()}')
                else:
                    handle.append.remote(msg.value().decode('utf-8'))

        threading.Thread(target=append).start()

    def recv_from(self, handle):
        # use kafka producer actor to push from rayvens stream to camel sink
        helper = ProducerActor.remote(self.name)
        handle.send_to.remote(helper, self.name)

    def cancel(self):
        try:
            os.kill(self.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
