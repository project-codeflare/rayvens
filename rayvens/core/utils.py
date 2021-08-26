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
import random
import time
import threading
from queue import Queue, Empty

# Port externalized by the cluster.
externalized_cluster_port = "31095"

# Check if the executable exists in PATH. This method should work
# in Windows, Linux and MacOS. Python >= 3.3 required.

rayvens_random = random.Random()
rayvens_random.seed()


def random_port(check_port):
    port = rayvens_random.randint(49152, 65535)
    if not check_port:
        return port

    while not _port_is_free(port):
        print(f"Port {port} busy, trying new port.")
        port = rayvens_random.randint(49152, 65535)

    return port


def _port_is_free(port):
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Attempt to bind to the port if it fails, port must be busy.
    port_is_free = True
    try:
        sock.bind(('127.0.0.1', port))
    except socket.error as message:
        print(f'Port {port} is in use (Error: {str(message)}).')
        port_is_free = False

    sock.close()
    return port_is_free


def executable_is_available(executable):
    # If this is a path to the executable file return true.
    if os.path.isfile(executable):
        return True

    # Look up executable in path.
    from shutil import which
    return which(executable) is not None


def subprocess_tag(subprocess_name):
    return "[%s subprocess]" % subprocess_name


def print_log_from_subprocess(subprocess_name, stdout, with_output):
    output = stdout.readline().decode("utf-8")
    output = output.strip()

    if output != "" and with_output:
        print(subprocess_tag(subprocess_name), output)

    return output


class LogThread(threading.Thread):
    def __init__(self, stdout):
        threading.Thread.__init__(self)
        self.stop_flag = threading.Event()
        self.stdout = stdout
        self.queue = Queue()

    def run(self):
        while not self.stop_flag.is_set():
            line = self.stdout.readline().decode("utf-8")
            self.queue.put(line.strip())
            time.sleep(0.1)

        print("[Log thread] Kamel command logging terminated.")


def print_log_from_queue(subprocess_name, queue, with_output):
    try:
        line = queue.get_nowait()
    except Empty:
        return None
    else:
        if line != "" and with_output:
            print(subprocess_tag(subprocess_name), line)
        return line


def print_log(subprocess_name, message):
    print(subprocess_tag(subprocess_name), message)


def get_server_pod_name():
    with open('/etc/podinfo/labels', 'r') as f:
        for line in f:
            k, v = line.partition('=')[::2]
            if k == 'component':
                return f'{v[1:-2]}'

    raise RuntimeError("Cannot find server pod name")


def create_partitioned_topic(topic, partitions, brokers):
    # Create new topic
    from confluent_kafka.admin import AdminClient, NewTopic
    admin_client = AdminClient({"bootstrap.servers": brokers})

    # TODO: Smart choice for replication factor, for now use a
    # replication factor of 1.
    topics = [NewTopic(topic, num_partitions=partitions, replication_factor=1)]
    admin_client.create_topics(topics)

    # Wait for topic to be ready:
    topic_ready = False
    while not topic_ready:
        for enabled_topic in admin_client.list_topics().topics:
            if topic == enabled_topic:
                topic_ready = True
                break
    print(f"Topic {topic} is ready.")
