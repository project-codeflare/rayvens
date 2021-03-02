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
        filename = f'{name}.yaml'
        with open(filename, 'w') as f:
            yaml.dump(integration, f)
        process = subprocess.Popen(
            ['kamel', 'local', 'run', filename], start_new_session=True)
        self.pid = process.pid
        _integrations.append(self)

    def url(self):
        return 'http://localhost:8080'

    def cancel(self):
        os.killpg(os.getpgid(self.pid), signal.SIGTERM)
