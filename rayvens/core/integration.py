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

from rayvens.core.utils import random_port
from rayvens.core.name import name_integration
from rayvens.core import kamel
from rayvens.core import kubernetes


class Integration:
    def __init__(self, stream_name, source_sink_name, config):
        if 'integration_type' not in config:
            raise RuntimeError(
                "Unreachable: integration must have an integration_type.")
        self.stream_name = stream_name
        self.source_sink_name = source_sink_name
        self.config = config
        self.integration_name = name_integration(self.stream_name,
                                                 self.source_sink_name)
        self.port = random_port()
        self.invocation = None
        self.service_name = None
        self.server_address = None

    def invoke_local_run(self, mode, integration_content):
        self.invocation = kamel.local_run(
            [integration_content],
            mode,
            self.integration_name,
            port=self.port,
            integration_type=self.config['integration_type'])

    def invoke_run(self, mode, integration_content):
        self.invocation = kamel.run(
            [integration_content],
            mode,
            self.integration_name,
            integration_type=self.config['integration_type'])

        # If running in mixed mode, i.e. Ray locally and kamel in the cluster,
        # then we have to also start a service the allows outside processes to
        # send data to the sink.
        if mode.is_mixed():
            self.service_name = "-".join(["service", self.integration_name])
            kubernetes.create_kamel_external_service(mode, self.service_name,
                                                     self.integration_name)

    # Function which disconnects an integration whether it is an integration
    # created using the kamel operator and `kamel run` or an integration
    # created using `kamel local run`.
    def disconnect(self, mode):
        if self.invocation.uses_operator():
            # If kamel is running the cluster then use kamel delete to
            # terminate the integration. First we terminate any services
            # associated with the integration.
            if self.service_name is not None:
                if not kubernetes.delete_service(mode, self.service_name):
                    raise RuntimeError(
                        f'Service with name {self.service_name} for'
                        '{self.integration_name} could not be'
                        'terminated')

            # Terminate the integration itself.
            if not kamel.delete(self.invocation, self.integration_name):
                raise RuntimeError(
                    f'Failed to terminate {self.integration_name}')
            return

        # If no kamel operator is used the only other alternative is that the
        # integration is running locally. In that case we only need to kill the
        # process that runs it.
        self.invocation.kill()

    def route(self, default=None):
        if 'route' in self.config and self.config['route'] is not None:
            return self.config['route']
        if default is not None:
            return default
        return f'/{self.stream_name}'

    def use_backend(self):
        if 'use_backend' in self.config and self.config[
                'use_backend'] is not None:
            return self.config['use_backend']
        return False
