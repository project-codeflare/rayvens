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

# Send message to Slack sink using the kafka transport.

# Command line arguments and validation:
if len(sys.argv) < 4:
    print(f'usage: {sys.argv[0]} <brokers> <password> <slack_channel>'
          '<slack_webhook> <run_mode> OR'
          f'       {sys.argv[0]} <slack_channel> <slack_webhook> <run_mode>')
    sys.exit(1)

# Brokers and run mode:
brokers = None
password = None
slack_channel = sys.argv[1]
slack_webhook = sys.argv[2]
run_mode = sys.argv[3]
if len(sys.argv) == 6:
    brokers = sys.argv[1]
    password = sys.argv[2]
    slack_channel = sys.argv[3]
    slack_webhook = sys.argv[4]
    run_mode = sys.argv[5]

if run_mode not in ['local', 'mixed', 'operator']:
    raise RuntimeError(f'Invalid run mode provided: {run_mode}')

# The Kafka topic used for communication.
topic = "externalTopicSink"

# Initialize ray either on the cluster or locally otherwise.
if run_mode == 'operator':
    ray.init(address='auto')
else:
    ray.init()

# Start rayvens in operator mode."
rayvens.init(mode=run_mode, transport="kafka")

# Create stream.
stream = rayvens.Stream('slack')

# Event sink config.
sink_config = dict(kind='slack-sink',
                   channel=slack_channel,
                   webhookUrl=slack_webhook,
                   kafka_transport_topic=topic,
                   kafka_transport_partitions=3)

# Add sink to stream.
sink = stream.add_sink(sink_config)

# Sends message to all sinks attached to this stream.
stream << f'Message to Slack sink in run mode {run_mode} and Kafka transport.'

# Disconnect any sources or sinks attached to the stream 2 seconds after
# the stream is idle (i.e. no events were propagated by the stream).
stream.disconnect_all(after_idle_for=2)
