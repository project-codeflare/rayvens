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

from rayvens.core import invocation


# Method to create a kafka topic with partitions.
def create_topic(topic, partitions, brokers):
    command = ["--create"]

    # Topic:
    command.append("--topic")
    command.append(topic)

    # Partitions:
    command.append("--partitions")
    command.append(str(partitions))

    # Bootstrap server:
    command.append("--bootstrap-server")
    command.append(brokers)

    # Only create topic if it does not exist already:
    command.append("--if-not-exists")

    return _invoke_kafka_command(command)


# Method to delete a kafka topic.
def delete_topic():
    # TODO
    pass


def _invoke_kafka_command(command):
    # Invoke command using the Kamel invocation actor.
    kafka_invocation = invocation.KafkaInvocation(command)

    # Wait for kamel command to finish launching the integration.
    if kafka_invocation.invoke():
        return kafka_invocation

    return None
