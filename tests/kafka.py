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

import os
import ray
import rayvens
import time

# Initialize run mode.
run_mode = 'operator'
env_run_mode = os.getenv('RAYVENS_TEST_MODE')
if env_run_mode is not None:
    run_mode = env_run_mode

if run_mode == 'operator':
    ray.init(address='auto')
else:
    ray.init(object_store_memory=78643200)

# The Kafka topic used for communication.
topic = "testTopic"

# If using the Kafka broker started by Rayvens the following brokers
# are possible:
# - from inside the cluster: kafka:9092
# - from outside the cluster: localhost:31093
broker = 'localhost:31093'
if run_mode == 'operator':
    broker = "kafka:9092"

rayvens.init(mode=run_mode)

# Create sink stream and configuration.
sink_stream = rayvens.Stream('kafka-sink-stream')
sink_config = dict(kind='kafka-sink',
                   route='/tokafka',
                   topic=topic,
                   brokers=broker)
sink = sink_stream.add_sink(sink_config)

# Create source stream and configuration.
source_stream = rayvens.Stream('kafka-source-stream')
source_config = dict(kind='kafka-source',
                     route='/fromkafka',
                     topic=topic,
                     brokers=broker)
source = source_stream.add_source(source_config)
# Log all events from stream-attached sources.
source_stream >> (lambda event: print('MESSAGE:', event))

# Sends message to all sinks attached to this stream.
time.sleep(5)
output_message = f'Sending message to Kafka sink in run mode {run_mode}.'
sink_stream << output_message

# Disconnect source and sink.
time.sleep(5)
source_stream.disconnect_all()
sink_stream.disconnect_all()
