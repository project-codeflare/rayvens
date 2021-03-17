import atexit
import os
import ray
import signal
import subprocess
import yaml
import time
import threading
import requests
import random
import rayvens.core.catalog as catalog

integrations = []


def killall():
    global integrations
    for integration in integrations:
        integration.cancel()


# instantiate camel actor manager and setup exit hook
def start(prefix, mode):
    camel = Camel.remote(mode)
    atexit.register(camel.killall.remote)
    return camel


# the actor to manage camel
@ray.remote(num_cpus=0)
class Camel:
    def __init__(self, mode):
        self.streams = []
        self.mode = mode

    def add_source(self, name, stream, config):
        self.streams.append(stream)
        spec = catalog.construct_source(config,
                                        'platform-http:/source',
                                        inverted=True)

        def run():
            integration = Integration(name, spec)
            integration.send_to(stream)

        if 'spread' not in self.mode:
            run()
        else:
            stream._exec.remote(run)

    def add_sink(self, name, stream, config):
        self.streams.append(stream)
        spec = catalog.construct_sink(config, 'platform-http:/sink')

        def run():
            integration = Integration(name, spec)
            integration.recv_from(stream)

        if 'spread' not in self.mode:
            run()
        else:
            stream._exec.remote(run)

    def killall(self):
        if 'spread' not in self.mode:
            killall()
        else:
            for stream in self.streams:
                stream._exec.remote(killall)


# the low-level implementation-specific stuff

rayvens_random = random.Random()
rayvens_random.seed()


def random_port():
    return rayvens_random.randint(49152, 65535)


@ray.remote(num_cpus=0)
class ProducerActor:
    def __init__(self, url):
        self.url = url

    def append(self, data):
        try:
            requests.post(self.url, data)
        except requests.exceptions.ConnectionError:
            pass


class Integration:
    def __init__(self, name, spec):
        self.name = name
        filename = f'{name}.yaml'
        with open(filename, 'w') as f:
            yaml.dump(spec, f)
        self.port = random_port()
        queue = os.path.join(os.path.dirname(__file__), 'Queue.java')
        command = [
            'kamel', 'local', 'run', queue, '--property',
            f'quarkus.http.port={self.port}', filename
        ]
        process = subprocess.Popen(command, start_new_session=True)
        self.pid = process.pid
        global integrations
        integrations.append(self)

    def send_to(self, stream):
        def append():
            while True:
                try:
                    response = requests.get(
                        f'http://localhost:{self.port}/source')
                    if response.status_code != 200:
                        time.sleep(1)
                        continue
                    stream.append.remote(response.text)
                except requests.exceptions.ConnectionError:
                    time.sleep(1)

        threading.Thread(target=append).start()

    def recv_from(self, stream):
        # use kafka producer actor to push from rayvens stream to camel sink
        helper = ProducerActor.remote(f'http://localhost:{self.port}/sink')
        stream.send_to.remote(helper, self.name)

    def cancel(self):
        try:
            os.killpg(os.getpgid(self.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
