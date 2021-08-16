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

import rayvens.core.catalog as catalog
from rayvens.core.integration import Integration
from rayvens.core.common import get_run_mode, send_to, recv_from


def start(camel_mode):
    return Camel(get_run_mode(camel_mode))


class Camel:
    def __init__(self, mode):
        self.mode = mode
        self.mode.transport = 'http'

    def add_source(self, stream, config, source_name):
        integration = Integration(stream.name, source_name, config)
        route = integration.route(default='/source')
        spec = catalog.construct_source(config,
                                        f'platform-http:{route}',
                                        inverted=True)
        integration.prepare_environment(self.mode)
        integration.invoke_local_run(self.mode, spec)
        send_to(stream.actor, self.mode.server_address(integration), route)
        return integration

    def add_sink(self, stream, config, sink_name):
        integration = Integration(stream.name, sink_name, config)
        route = integration.route(default='/sink')
        spec = catalog.construct_sink(config, f'platform-http:{route}')
        integration.prepare_environment(self.mode)
        integration.invoke_local_run(self.mode, spec)
        recv_from(stream.actor, sink_name,
                  self.mode.server_address(integration), route)
        return integration

    def disconnect(self, integration):
        integration.disconnect(self.mode)
