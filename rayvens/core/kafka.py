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
from rayvens.core.common import get_run_mode, brokers
from rayvens.core.common import kafka_send_to, kafka_recv_from
from rayvens.core.integration import Integration


def start(camel_mode):
    return Camel(get_run_mode(camel_mode))


class Camel:
    def __init__(self, mode):
        self.mode = mode
        self.mode.transport = 'kafka'

    def add_source(self, stream, config, source_name):
        integration = Integration(stream.name, source_name, config)
        spec = catalog.construct_source(
            config,
            f'kafka:{integration.kafka_transport_topic}?brokers={brokers()}')
        integration.prepare_environment(self.mode)
        integration.invoke_local_run(self.mode, spec)
        kafka_send_to(integration.kafka_transport_topic, stream.actor)
        return integration

    def add_sink(self, stream, config, sink_name):
        integration = Integration(stream.name, sink_name, config)
        spec = catalog.construct_sink(
            config,
            f'kafka:{integration.kafka_transport_topic}?brokers={brokers()}')
        integration.prepare_environment(self.mode)
        integration.invoke_local_run(self.mode, spec)
        kafka_recv_from(sink_name, integration.kafka_transport_topic,
                        stream.actor)
        return integration

    def disconnect(self, integration):
        integration.disconnect(self.mode)
