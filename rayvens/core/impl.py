import atexit
import os
import ray
import signal
import subprocess
import yaml
from confluent_kafka import Consumer, Producer
import threading


# instantiate camel actor manager and setup exit hook
def start(prefix, mode):
    camel = Camel.remote()
    atexit.register(camel.exit.remote)
    return camel


# construct a camel source specification from a rayvens source config
def construct_source(config):
    if config['kind'] is None:
        raise TypeError('A Camel source needs a kind.')
    if config['kind'] not in ['http-source']:
        raise TypeError('Unsupported Camel source.')
    url = config['url']
    period = config.get('period', 1000)

    return lambda endpoint: [{
        'from': {
            'uri': f'timer:tick?period={period}',
            'steps': [{
                'to': url
            }, {
                'to': endpoint
            }]
        }
    }]


# construct a camel sink specification from a rayvens source config
def construct_sink(config):
    if config['kind'] is None:
        raise TypeError('A Camel sink needs a kind.')
    if config['kind'] not in ['slack-sink']:
        raise TypeError('Unsupported Camel sink.')
    channel = config['channel']
    webhookUrl = config['webhookUrl']

    return lambda endpoint: [{
        'from': {
            'uri': endpoint,
            'steps': [{
                'to': f'slack:{channel}?webhookUrl={webhookUrl}',
            }]
        }
    }]


# the actor to manage camel
@ray.remote(num_cpus=0)
class Camel:
    def __init__(self):
        self.integrations = []

    def add_source(self, name, stream, config):
        spec = construct_source(config)
        integration = Integration(name, spec)
        integration.send_to(stream)
        self.integrations.append(integration)

    def add_sink(self, name, stream, config):
        spec = construct_sink(config)
        integration = Integration(name, spec)
        integration.recv_from(stream)
        self.integrations.append(integration)

    def exit(self):
        integrations = self.integrations
        self.integrations = None
        for i in integrations:
            i.cancel()


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
            yaml.dump(spec(f'kafka:{name}?brokers=${brokers()}'), f)
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
