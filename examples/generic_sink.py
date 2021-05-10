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
import time
import sys

# Receive message from stock price source and print it to console using the
# operator implementation.

# Initialize ray.
if len(sys.argv) < 4:
    print(f'usage: {sys.argv[0]} <slack_channel> <slack_webhook> <run_mode>')
    sys.exit(1)
slack_channel = sys.argv[1]
slack_webhook = sys.argv[2]
run_mode = sys.argv[3]

if run_mode not in ['local', 'operator']:
    raise RuntimeError(f'Invalid run mode provided: {run_mode}')

# Initialize ray either on the cluster or locally otherwise.
if run_mode == 'operator':
    ray.init(address='auto')
else:
    ray.init()

# Start rayvens in the desired mode.
rayvens.init(mode=run_mode)

# Create stream.
stream = rayvens.Stream('slack')

# Event sink config.
sink_config = dict(kind='generic-sink',
                   spec=f"""
- from:
    uri: platform-http:/toslack
    steps:
      - to: slack:{slack_channel}?webhookUrl={slack_webhook}
    """)

# Attach source to stream.
sink = stream.add_sink(sink_config)

# Sends message to all sinks attached to this stream.
stream << f'Sending message to Slack generic sink in run mode {run_mode}.'

# Wait before ending program.
time.sleep(20)

stream.disconnect_all()
