import atexit
import os
import ray
import signal
import subprocess
import yaml
from confluent_kafka import Consumer, Producer
import threading


def start(prefix, mode):
    camel = Camel.remote()
    atexit.register(camel.exit.remote)
    return camel


def brokers():
    host = os.getenv('KAFKA_SERVICE_HOST', 'localhost')
    port = os.getenv('KAFKA_SERVICE_PORT', '31093')
    return f'{host}:{port}'


@ray.remote(num_cpus=0)
class Camel:
    def __init__(self):
        self.integrations = []

    def add_source(self, name, stream, source):
        if source['kind'] is None:
            raise TypeError('A Camel source needs a kind.')
        if source['kind'] not in ['http-source']:
            raise TypeError('Unsupported Camel source.')
        url = source['url']
        period = source.get('period', 1000)

        integration = Integration(name, [{
            'from': {
                'uri': f'timer:tick?period={period}',
                'steps': [{
                    'to': url
                }, {
                    'to': f'kafka:{name}?brokers=${brokers()}'
                }]
            }
        }])

        integration.send_to(stream)

        self.integrations.append(integration)

    def add_sink(self, name, stream, sink):
        if sink['kind'] is None:
            raise TypeError('A Camel sink needs a kind.')
        if sink['kind'] not in ['slack-sink']:
            raise TypeError('Unsupported Camel sink.')
        channel = sink['channel']
        webhookUrl = sink['webhookUrl']

        integration = Integration(name, [{
            'from': {
                'uri': f'kafka:{name}?brokers=${brokers()}',
                'steps': [{
                    'to': f'slack:{channel}?webhookUrl={webhookUrl}',
                }]
            }
        }])

        integration.recv_from(stream)

        self.integrations.append(integration)

    def exit(self):
        integrations = self.integrations
        self.integrations = None
        for i in integrations:
            i.cancel()


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


class Integration:
    def __init__(self, name, integration):
        self.name = name
        filename = f'{name}.yaml'
        with open(filename, 'w') as f:
            yaml.dump(integration, f)
        command = ['kamel', 'local', 'run', filename]
        process = subprocess.Popen(command, start_new_session=True)
        self.pid = process.pid

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
