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

import ray
import rayvens
import sys
import time

# An artificial example of using Kafka sources and sink.
# Typically the user application will interact with an external Kafka
# service to either subscribe or publish data to other services:
#
#    EXT. SERVICE => KAFKA => RAYVENS KAFKA SOURCE
# or
#    RAYVENS KAFKA SINK => KAFKA => EXT. SERVICE
#
# In this example we put together an artificial example where, to
# demonstrate both Kafka sources and sinks at the same time we
# set a Kafka sink to publish to a test topic then have a Kafka
# source read from that test topic:
#
#    RAYVENS KAFKA SINK => KAFKA => RAYVENS KAFKA SOURCE
#

# Command line arguments and validation:
if len(sys.argv) < 1:
    print(f'usage: {sys.argv[0]} <run_mode>')
    sys.exit(1)

# Run mode.
run_mode = sys.argv[1]
if run_mode not in ['local', 'mixed.operator', 'operator']:
    raise RuntimeError(f'Invalid run mode provided: {run_mode}')

# The Kafka topic used for communication.
topic = "externalTopicTopic"

# If using the Kafka broker started by Rayvens the following brokers
# are possible:
# - from inside the cluster: kafka:9092
# - from outside the cluster: localhost:31093
broker = 'localhost:31093'
if run_mode == 'operator':
    broker = "kafka:9092"

# Initialize ray either on the cluster or locally otherwise.
if run_mode == 'operator':
    ray.init(address='auto')
else:
    ray.init()

# Start rayvens in operator mode.
rayvens.init(mode=run_mode)

# Create source stream and configuration.
source_stream = rayvens.Stream('kafka-source-stream')
source_config = dict(kind='kafka-source',
                     route='/fromkafka',
                     topic=topic,
                     broker=broker)
source = source_stream.add_source(source_config)
# Log all events from stream-attached sources.
source_stream >> (lambda event: print('KAFKA SOURCE:', event))

# Create sink stream and configuration.
sink_stream = rayvens.Stream('kafka-sink-stream')
sink_config = dict(kind='kafka-sink',
                   route='/tokafka',
                   topic=topic,
                   broker=broker)
sink = sink_stream.add_sink(sink_config)

# Sends message to all sinks attached to this stream.
sink_stream << f'Sending message to Kafka sink in run mode {run_mode}.'

# Give a grace period to the message to propagate then disconnect source
# and sink.
time.sleep(5)
source_stream.disconnect_all()
sink_stream.disconnect_all()
