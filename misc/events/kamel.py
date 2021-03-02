import os
import requests
import subprocess
import yaml


class Integration:
    def __init__(self, name, integration):
        self.name = name
        filename = f'{name}.yaml'
        with open(filename, 'w') as f:
            yaml.dump(integration, f)
        process = subprocess.Popen(['kamel', 'local', 'run', filename])
        self.pid = process.pid

    def url(self):
        return 'http://localhost:8080'

    def cancel(self):
        os.kill(self.pid, signal.SIGTERM)
