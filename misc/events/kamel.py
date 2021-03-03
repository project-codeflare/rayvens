import atexit
import os
import signal
import requests
import subprocess
import yaml

_integrations = []


def _atexit():
    for i in _integrations:
        i.cancel()


atexit.register(_atexit)


class Integration:
    def __init__(self, name, in_cluster, integration):
        self.name = name
        self.in_cluster = in_cluster
        filename = f'{name}.yaml'
        with open(filename, 'w') as f:
            yaml.dump(integration, f)
        if in_cluster:
            command = ['/home/ray/kamel', 'run', '--dev', filename]
        else:
            command = ['kamel', 'local', 'run', filename]
        process = subprocess.Popen(command, start_new_session=True)
        self.pid = process.pid
        _integrations.append(self)

    def url(self):
        if self.in_cluster:
            return f'http://{self.name}.ray.svc.cluster.local:80'
        else:
            return 'http://localhost:8080'

    def cancel(self):
        try:
            os.killpg(os.getpgid(self.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
