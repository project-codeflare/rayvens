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
    def __init__(self, name, integration):
        self.name = name
        self.url = 'http://localhost:8080'
        filename = f'{name}.yaml'
        with open(filename, 'w') as f:
            yaml.dump(integration, f)
        command = ['kamel', 'local', 'run', filename]
        namespace = os.getenv('KUBE_POD_NAMESPACE')
        if namespace != None:
            self.url = f'http://{self.name}.{namespace}.svc.cluster.local:80'
            command = ['/home/ray/rayvens/rayvens/linux-x86_64/kamel',
                       'run', '--dev', filename]
        process = subprocess.Popen(command, start_new_session=True)
        self.pid = process.pid
        _integrations.append(self)

    def cancel(self):
        try:
            os.killpg(os.getpgid(self.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
