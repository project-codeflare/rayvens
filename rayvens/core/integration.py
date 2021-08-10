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

from rayvens.core.common import brokers
from rayvens.core.utils import random_port, create_partitioned_topic
from rayvens.core.name import name_integration
from rayvens.core import catalog
from rayvens.core import kamel
from rayvens.core import kubernetes


class Integration:
    def __init__(self, stream_name, source_sink_name, config):
        self.stream_name = stream_name
        self.source_sink_name = source_sink_name

        # Integration must be marked as either a source or sink.
        if 'integration_type' not in config:
            raise RuntimeError(
                "Unreachable: integration must have an integration_type.")
        self.config = config

        # Sinks may accept only certain message types ensure that only
        # messages with the correct type reach a particular sink.
        if self.config['integration_type'] == 'sink':
            self.input_restrictions = catalog.input_restriction(config)

        self.integration_name = name_integration(self.stream_name,
                                                 self.source_sink_name)

        # Establish kafka transport topic name:
        self.kafka_transport_topic = self.integration_name
        if "kafka_transport_topic" in config:
            self.kafka_transport_topic = config["kafka_transport_topic"]

        self.port = random_port()
        self.invocation = None
        self.service_name = None
        self.server_address = None
        self.environment_preparators = []

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

    # Check if the sink we are routing the message to has any restrictions
    # in terms of message type. A message will only be routed to a sink
    # if the sink accepts its type.
    def accepts_data_type(self, data):
        # If there are no restrictions return immediately:
        restricted_message_types = self.input_restrictions[
            'restricted_message_types']
        if len(restricted_message_types) == 0:
            return True
        for restricted_type in restricted_message_types:
            if isinstance(data, restricted_type):
                return True
        return False

    # Method that checks if, based on the configuration, the integration
    # requires something to be run or created before the integration is run.
    def prepare_environment(self, mode):
        # Create a multi-partition topic for a kafka source/sink.
        if (self.config['kind'] == 'kafka-source' or
            self.config['kind'] == 'kafka-sink') and \
           'partitions' in self.config and self.config['partitions'] > 1:
            topic = self.config['topic']
            partitions = self.config['partitions']
            kafka_brokers = self.config['brokers']

            # Create topic
            create_partitioned_topic(topic, partitions, kafka_brokers)

        # Create a multi-partition topic for the Kafka transport of a
        # source/sink.
        if mode.transport == "kafka" and \
           'kafka_transport_partitions' in self.config and \
           self.config['kafka_transport_partitions'] > 1:
            partitions = self.config['kafka_transport_partitions']

            # Create topic
            create_partitioned_topic(self.kafka_transport_topic, partitions,
                                     brokers())

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
