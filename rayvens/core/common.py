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
import json
from pathlib import Path
from confluent_kafka import Consumer, Producer
from rayvens.core import kamel
from rayvens.core.mode import mode, RayvensMode
from ray.actor import ActorHandle, ActorMethod
from ray.remote_function import RemoteFunction


def get_run_mode(camel_mode, check_port):
    if camel_mode == 'auto' or camel_mode == 'local':
        mode.run_mode = RayvensMode.LOCAL
    elif camel_mode == 'mixed':
        mode.run_mode = RayvensMode.MIXED_OPERATOR
    elif camel_mode == 'operator':
        mode.run_mode = RayvensMode.CLUSTER_OPERATOR
    else:
        raise RuntimeError("Unsupported camel mode.")
    mode.check_port = check_port
    return mode


def _wait_for_ready_integration(mode, integration):
    server_address = mode.server_address(integration)
    health_check_address = f"{server_address}/q/health"

    healthy_integration = False
    max_retries = 100
    while True:
        try:
            response = requests.get(health_check_address, timeout=(5, 5))
        except requests.exceptions.ConnectionError:
            time.sleep(1)
            max_retries -= 1
            if max_retries == 0:
                break
            continue
        json_response = json.loads(response.content)
        all_routes_are_up = True
        for check in json_response['checks']:
            if check['name'] == 'camel-readiness-checks' and check[
                    'status'] == 'UP':
                data = check['data']
                if data['context'] == 'UP':
                    # Ensure all routes are up.
                    route_index = 1
                    route = f'route:route{route_index}'
                    while route in data:
                        if data[route] != 'UP':
                            all_routes_are_up = False
                            break
                        route_index += 1
                        route = f'route:route{route_index}'
        if all_routes_are_up:
            healthy_integration = True
            break
        time.sleep(1)

    return healthy_integration


# Wait for an integration to reach its running state and not only that but
# also be in a state where it can immediately execute incoming requests.
def await_start(mode, integration):
    # Only needed when operator is used.
    if mode.is_local():
        return True

    # Check logs of the integration to make sure it was installed properly.
    invocation = kamel.log(mode, integration.integration_name,
                           "Installed features:")
    integration_is_running = invocation is not None
    if integration_is_running:
        print(f'Integration {integration.integration_name} is running.')
    else:
        print('Integration did not start correctly.')

    # Perform health check and wait for integration to be ready.
    healthy_integration = _wait_for_ready_integration(mode, integration)

    if healthy_integration:
        print(f'Integration {integration.integration_name} is healthy.')
        return integration_is_running

    print(f'Integration {integration.integration_name} is not healthy.')
    return False


@ray.remote(num_cpus=0)
class ProducerActor:
    def __init__(self, url):
        self.url = url

    def append(self, data):
        try:
            if isinstance(data, Path):
                requests.post(self.url, str(data), timeout=(5, None))
            else:
                requests.post(self.url, data, timeout=(5, None))
        except requests.exceptions.ConnectionError:
            pass


# Method for sending events to the queue.
def send_to(handle, server_address, route):
    def append():
        while True:
            try:
                response = requests.get(f'{server_address}{route}',
                                        timeout=(5, None))
                if response.status_code != 200:
                    time.sleep(1)
                    continue
                response.encoding = 'latin-1'
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
        if isinstance(data, Path):
            self.producer.produce(str(data))
        else:
            self.producer.produce(data)


class ProducerHelper:
    def __init__(self, name):
        self.name = name
        self.producer = Producer({'bootstrap.servers': brokers()})

    def produce(self, data):
        if data is not None:
            self.producer.produce(self.name, data.encode('utf-8'))


@ray.remote(num_cpus=0.05)
class KafkaConsumer(object):
    def __init__(self, kafka_transport_topic, stream_actor):
        self.stream_actor = stream_actor

        # Set up a Kafka Consumer:
        from confluent_kafka import Consumer
        self.kafka_consumer = Consumer({
            'bootstrap.servers': brokers(),
            'group.id': 'ray',
            'enable.auto.commit': True,
            'auto.offset.reset': 'earliest'
        })

        # Subscribe the Kafka Consumer to the transport topic:
        self.kafka_consumer.subscribe([kafka_transport_topic])

    def enable_consumer(self, subscribers, operator):
        self.enabled = True
        while self.enabled:
            # Retrieve message:
            msg = self.kafka_consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"Consumer error: {msg.error()}")
                continue

            # Decode:
            data = msg.value().decode('utf-8')

            # Check message is valid:
            if data is None:
                continue

            # Apply the operator:
            if operator is not None:
                data = ray.get(eval(operator, data))

            # Send message to subscribers:
            for name, stream_subscriber in subscribers.items():
                eval(stream_subscriber, data)
            self.stream_actor._update_timestamp.remote(time.time())

    def disable_consumer(self):
        self.enabled = False

    def close_consumer(self):
        self.kafka_consumer.close()


def kafka_send_to(kafka_transport_topic, kafka_transport_partitions, handle):
    if kafka_transport_partitions > 1:
        consumers = [
            KafkaConsumer.remote(kafka_transport_topic, handle)
            for _ in range(kafka_transport_partitions)
        ]

        def append():
            subscribers, operator = ray.get(handle._fetch_processors.remote())
            try:
                consumer_references = [
                    consumer.enable_consumer.remote(subscribers, operator)
                    for consumer in consumers
                ]
                ray.get(consumer_references)
            except KeyboardInterrupt:
                for consumer in consumers:
                    consumer.disable_consumer.remote()
            finally:
                for consumer in consumers:
                    consumer.close_consumer.remote()

        threading.Thread(target=append).start()
        return

    # Use kafka consumer thread to push from camel source to rayvens stream
    consumer = Consumer({
        'bootstrap.servers': brokers(),
        'group.id': 'ray',
        'auto.offset.reset': 'latest'
    })

    consumer.subscribe([kafka_transport_topic])

    def append():
        while True:
            msg = consumer.poll()
            if msg.error():
                print(f'consumer error: {msg.error()}')
            else:
                handle.append.remote(msg.value().decode('utf-8'))

    threading.Thread(target=append).start()


def kafka_recv_from(integration_name, kafka_transport_topic, handle):
    # use kafka producer actor to push from rayvens stream to camel sink
    helper = KafkaProducerActor.remote(kafka_transport_topic)
    handle.send_to.remote(helper, integration_name)


def brokers():
    host = os.getenv('KAFKA_SERVICE_HOST', 'localhost')
    port = os.getenv('KAFKA_SERVICE_PORT', '31093')
    return f'{host}:{port}'


def operator_brokers():
    host = os.getenv('KAFKA_SERVICE_HOST', 'kafka')
    port = os.getenv('KAFKA_SERVICE_PORT', '9092')
    return f'{host}:{port}'


def eval(f, data):
    if isinstance(f, ActorHandle):
        return f.append.remote(data)
    elif isinstance(f, ActorMethod) or isinstance(f, RemoteFunction):
        return f.remote(data)
    else:
        return f(data)
