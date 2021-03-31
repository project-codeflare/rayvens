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

import requests
import time
import threading
from rayvens.core import kamel
from rayvens.core import common
from rayvens.core.catalog import construct_source, construct_sink
from rayvens.core.integration import Integration


def start(camel_mode):
    return Camel(common.get_run_mode(camel_mode))


class Camel:
    def __init__(self, mode):
        self.mode = mode

    def add_source(self, stream, source, source_name):
        # Construct integration
        integration = Integration(stream.name, source_name, source)

        # Construct endpoint. First, get route:
        route = integration.route()

        # Determine the `to` endpoint value made up of a base address and
        # a custom route provided by the user. Use this to construct the
        # integration source code.
        integration_content = construct_source(source,
                                               f'platform-http:{route}',
                                               inverted=True)

        # Start running the source integration.
        source_invocation = kamel.run([integration_content],
                                      self.mode,
                                      integration.integration_name,
                                      integration_as_files=False,
                                      inverted_http=True)
        integration.invocation = source_invocation

        # Set up source for the HTTP connector case.
        server_address = self.mode.getQuarkusHTTPServer(
            integration.integration_name)
        send_to_helper = SendToHelper()
        send_to_helper.send_to(stream.actor, server_address, route)

        if not common.await_start(self.mode, integration.integration_name):
            raise RuntimeError('Could not start source')
        return integration

    def add_sink(self, stream, sink, sink_name):
        # Construct integration
        integration = Integration(stream.name, sink_name, sink)

        # Extract integration properties:
        route = integration.route()
        integration_name = integration.integration_name

        # Get integration source code.
        integration_content = construct_sink(sink, f'platform-http:{route}')

        # Start running the integration.
        sink_invocation = kamel.run([integration_content],
                                    self.mode,
                                    integration_name,
                                    integration_as_files=False)
        integration.invocation = sink_invocation

        if self.mode.isMixed():
            integration.service_name = common.create_externalizing_service(
                self.mode, integration)

        helper = common.Helper.remote(
            self.mode.getQuarkusHTTPServer(integration_name) + route)
        stream.actor.send_to.remote(helper, sink_name)

        # Wait for integration to finish.
        if not common.await_start(self.mode, integration_name):
            raise RuntimeError('Could not start sink')

        return integration

    def disconnect(self, integration):
        kamel_operator = self.mode.isCluster() or self.mode.isMixed()
        common.disconnect_integration(self.mode,
                                      integration,
                                      kamel_operator=kamel_operator)


class SendToHelper:
    def send_to(self, handle, server_address, route):
        def append():
            while True:
                try:
                    response = requests.get(f'{server_address}{route}')
                    if response.status_code != 200:
                        time.sleep(1)
                        continue
                    handle.append.remote(response.text)
                except requests.exceptions.ConnectionError:
                    time.sleep(1)

        threading.Thread(target=append).start()
