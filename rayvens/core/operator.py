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

from rayvens.core.common import get_run_mode, send_to, await_start
from rayvens.core.common import ProducerActor
from rayvens.core.catalog import construct_source, construct_sink
from rayvens.core.integration import Integration


def start(camel_mode):
    return Camel(get_run_mode(camel_mode))


class Camel:
    def __init__(self, mode):
        self.mode = mode
        self.mode.transport = 'http'

    def add_source(self, stream, source, source_name):
        # Construct integration
        integration = Integration(stream.name, source_name, source)

        # Construct endpoint. First, get route:
        route = integration.route()

        # Prepare env:
        integration.prepare_environment(self.mode)

        # Determine the `to` endpoint value made up of a base address and
        # a custom route provided by the user. Use this to construct the
        # integration source code.
        integration_content = construct_source(source,
                                               f'platform-http:{route}',
                                               inverted=True)

        # Start running the source integration.
        integration.invoke_run(self.mode, integration_content)

        # Set up source for the HTTP connector case.
        send_to(stream.actor, self.mode.server_address(integration), route)

        if not await_start(self.mode, integration):
            raise RuntimeError('Could not start source')
        return integration

    def add_sink(self, stream, sink, sink_name):
        # Construct integration
        integration = Integration(stream.name, sink_name, sink)

        # Extract integration properties:
        route = integration.route()

        # Prepare env:
        integration.prepare_environment(self.mode)

        # Get integration source code.
        integration_content = construct_sink(sink, f'platform-http:{route}')

        # Start running the integration.
        integration.invoke_run(self.mode, integration_content)

        helper = ProducerActor.remote(
            self.mode.server_address(integration) + route)
        stream.actor.send_to.remote(helper, sink_name)

        # Wait for integration to finish.
        if not await_start(self.mode, integration):
            raise RuntimeError('Could not start sink')

        return integration

    def disconnect(self, integration):
        integration.disconnect(self.mode)
