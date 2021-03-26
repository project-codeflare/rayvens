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
import time
import threading
import requests
import random
import rayvens.core.catalog as catalog
import sys


class Camel:
    def add_source(self, stream, config, name):
        spec = catalog.construct_source(config,
                                        'platform-http:/source',
                                        inverted=True)
        integration = Integration(name, spec)
        integration.send_to(stream.actor)

    def add_sink(self, stream, config, name):
        spec = catalog.construct_sink(config, 'platform-http:/sink')
        integration = Integration(name, spec)
        integration.recv_from(stream.actor)


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
        harness = os.path.join(os.path.dirname(__file__), 'harness.py')
        queue = os.path.join(os.path.dirname(__file__), 'Queue.java')
        command = [
            sys.executable, harness, 'kamel', 'local', 'run', queue,
            '--property', f'quarkus.http.port={self.port}', filename
        ]
        process = subprocess.Popen(command, start_new_session=True)
        self.pid = process.pid

    def send_to(self, handle):
        def append():
            while True:
                try:
                    response = requests.get(
                        f'http://localhost:{self.port}/source')
                    if response.status_code != 200:
                        time.sleep(1)
                        continue
                    handle.append.remote(response.text)
                except requests.exceptions.ConnectionError:
                    time.sleep(1)

        threading.Thread(target=append).start()

    def recv_from(self, handle):
        helper = ProducerActor.remote(f'http://localhost:{self.port}/sink')
        handle.send_to.remote(helper, self.name)

    def cancel(self):
        try:
            os.kill(self.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
