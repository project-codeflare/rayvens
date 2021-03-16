import atexit
import os
import ray
import requests
import signal
import subprocess
import yaml
from confluent_kafka import Consumer
import threading


def start(_, mode):
    if os.getenv('KUBE_POD_NAMESPACE') is not None and mode != 'local':
        camel = Camel.options(resources={'head': 1}).remote('operator')
    else:
        camel = Camel.remote('local')
    atexit.register(camel.exit.remote)
    return camel


@ray.remote(num_cpus=0)
class Camel:
    def __init__(self, mode):
        self.integrations = []
        self.mode = mode

    def add_source(self, name, stream, source):
        if source['kind'] is None:
            raise TypeError('A Camel source needs a kind.')
        if source['kind'] not in ['http-source']:
            raise TypeError('Unsupported Camel source.')
        url = source['url']
        period = source.get('period', 1000)

        brokers = 'localhost:31093'
        if os.getenv('KUBE_POD_NAMESPACE') is not None:
            brokers = 'kafka:9092'

        integration = Integration(name, self.mode, [{
            'from': {
                'uri': f'timer:tick?period={period}',
                'steps': [{
                    'to': url
                }, {
                    'to': f'kafka:{name}?brokers=${brokers}'
                }]
            }
        }], stream)

        if self.integrations is None:
            integration.cancel()
        else:
            self.integrations.append(integration)

    def add_sink(self, name, stream, sink):
        if sink['kind'] is None:
            raise TypeError('A Camel sink needs a kind.')
        if sink['kind'] not in ['slack-sink']:
            raise TypeError('Unsupported Camel sink.')
        channel = sink['channel']
        webhookUrl = sink['webhookUrl']
        integration = Integration(name, self.mode, [{
            'from': {
                'uri': f'platform-http:/{name}',
                'steps': [{
                    'to': f'slack:{channel}?webhookUrl={webhookUrl}',
                }]
            }
        }], None)

        url = f'{integration.url}/{name}'
        helper = Helper.remote(url)
        stream.send_to.remote(helper, name)
        if self.integrations is None:
            integration.cancel()
        else:
            self.integrations.append(integration)

    def exit(self):
        integrations = self.integrations
        self.integrations = None
        for i in integrations:
            i.cancel()


@ray.remote(num_cpus=0)
class Helper:
    def __init__(self, url):
        self.url = url

    def append(self, data):
        if data is not None:
            requests.post(self.url, data)


class Integration:
    def __init__(self, name, mode, integration, stream):
        self.name = name
        self.url = 'http://localhost:8080'
        filename = f'{name}.yaml'
        with open(filename, 'w') as f:
            yaml.dump(integration, f)
        command = ['kamel', 'local', 'run', filename]
        if mode == 'operator':
            namespace = os.getenv('KUBE_POD_NAMESPACE')
            self.url = f'http://{self.name}.{namespace}.svc.cluster.local:80'
            command = ['kamel', 'run', '--dev', filename]
        process = subprocess.Popen(command, start_new_session=True)
        self.pid = process.pid

        if stream is not None:
            brokers = 'localhost:31093'
            if os.getenv('KUBE_POD_NAMESPACE') is not None:
                brokers = 'kafka:9092'

            c = Consumer({
                'bootstrap.servers': brokers,
                'group.id': 'ray',
                'auto.offset.reset': 'latest'
            })

            c.subscribe([name])

            def recv():
                while True:
                    msg = c.poll()
                    if msg.error():
                        print(f'consumer error: ${msg.error()}')
                    else:
                        stream.append.remote(msg.value().decode('utf-8'))

            threading.Thread(target=recv).start()

    def cancel(self):
        try:
            os.killpg(os.getpgid(self.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
