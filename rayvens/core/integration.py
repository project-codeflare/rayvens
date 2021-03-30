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

from rayvens.core.name import name_integration


class Integration:
    def __init__(self, stream_name, source_sink_name, config):
        self.stream_name = stream_name
        self.source_sink_name = source_sink_name
        self.config = config
        self.integration_name = name_integration(self.stream_name,
                                                 self.source_sink_name)
        self.invocation = None
        self.service = None

    def route(self):
        if 'route' in self.config and self.config['route'] is not None:
            return self.config['route']
        return f'/{self.stream_name}'

    def use_backend(self):
        if 'use_backend' in self.config and self.config[
                'use_backend'] is not None:
            return self.config['use_backend']
        return False
