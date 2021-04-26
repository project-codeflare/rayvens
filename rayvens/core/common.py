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

import ray
import requests
import time
import threading
import os
from confluent_kafka import Consumer, Producer
from rayvens.core import kubernetes
from rayvens.core.mode import mode, RayvensMode


def get_run_mode(camel_mode):
    if camel_mode == 'auto' or camel_mode == 'local':
        mode.run_mode = RayvensMode.LOCAL
    elif camel_mode == 'mixed.operator':
        mode.run_mode = RayvensMode.MIXED_OPERATOR
    elif camel_mode == 'operator':
        mode.run_mode = RayvensMode.CLUSTER_OPERATOR
    else:
        raise RuntimeError("Unsupported camel mode.")
    return mode


# Wait for an integration to reach its running state and not only that but
# also be in a state where it can immediately execute incoming requests.
def await_start(mode, integration_name):
    # TODO: remove this once we enable this for local mode.
    if mode.isLocal():
        return True

    # Wait for pod to start.
    pod_is_running, pod_name = kubernetes.getPodRunningStatus(
        mode, integration_name)
    if pod_is_running:
        print(f'Pod {pod_name} is running.')
    else:
        print('Pod did not run correctly.')
        return False

    # Wait for integration to be installed. Since we now know that the pod
    # is running we can use that to check that the integration is installed
    # correctly.
    integration_is_running = kubernetes.getIntegrationStatus(mode, pod_name)
    if integration_is_running:
        print(f'Integration {integration_name} is running.')
    else:
        print('Integration did not start correctly.')

    return integration_is_running


@ray.remote(num_cpus=0)
class ProducerActor:
    def __init__(self, url):
        self.url = url

    def append(self, data):
        try:
            requests.post(self.url, data)
        except requests.exceptions.ConnectionError:
            pass


# Method for sending events to the queue.
def send_to(handle, server_address, route):
    def append():
        while True:
            try:
                response = requests.get(f'{server_address}{route}')
                if response.status_code != 200:
                    time.sleep(1)
                    continue
                handle.append.remote(response.text)
            except requests.exceptions.ConnectionError:
                time.sleep(1)

    threading.Thread(target=append).start()


# Method for sending events to the sink.
def recv_from(handle, integration_name, server_address, route):
    helper = ProducerActor.remote(f'{server_address}{route}')
    handle.send_to.remote(helper, integration_name)


@ray.remote(num_cpus=0)
class KafkaProducerActor:
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


def kafka_send_to(integration_name, handle):
    # use kafka consumer thread to push from camel source to rayvens stream
    consumer = Consumer({
        'bootstrap.servers': brokers(),
        'group.id': 'ray',
        'auto.offset.reset': 'latest'
    })

    consumer.subscribe([integration_name])

    def append():
        while True:
            msg = consumer.poll()
            if msg.error():
                print(f'consumer error: {msg.error()}')
            else:
                handle.append.remote(msg.value().decode('utf-8'))

    threading.Thread(target=append).start()


def kafka_recv_from(integration_name, handle):
    # use kafka producer actor to push from rayvens stream to camel sink
    helper = KafkaProducerActor.remote(integration_name)
    handle.send_to.remote(helper, integration_name)


def brokers():
    host = os.getenv('KAFKA_SERVICE_HOST', 'localhost')
    port = os.getenv('KAFKA_SERVICE_PORT', '31093')
    return f'{host}:{port}'
