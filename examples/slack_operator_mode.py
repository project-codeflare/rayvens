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

# Send message to Slack sink using the kamel anywhere operator implementation.

# Command line arguments and validation:
if len(sys.argv) < 4:
    print(f'usage: {sys.argv[0]} <slack_channel> <slack_webhook> <run_mode>')
    sys.exit(1)
slack_channel = sys.argv[1]
slack_webhook = sys.argv[2]
run_mode = sys.argv[3]
if run_mode not in ['local', 'mixed.operator', 'cluster.operator']:
    raise RuntimeError(f'Invalid run mode provided: {run_mode}')

# Initialize ray either on the cluster or locally otherwise.
if run_mode == 'cluster.operator':
    ray.init(address='auto')
else:
    ray.init()

# Start rayvens client in operator mode.
client = rayvens.Client(camel_mode=run_mode)

# Create stream.
stream = client.Stream('slack')

# Event sink config.
sink_config = dict(kind='slack-sink',
                   route='/toslack',
                   channel=slack_channel,
                   webhookUrl=slack_webhook)

# Add sink to stream.
sink = client.add_sink(stream, sink_config)

# Sends message to all sinks attached to this stream.
stream << f'Sending message to Slack sink in run mode {run_mode}.'

time.sleep(5)
