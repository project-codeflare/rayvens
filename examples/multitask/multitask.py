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

# Send message to Slack sink using a multi-tasking operator.

# Command line arguments and validation:
if len(sys.argv) < 4:
    print(f'usage: {sys.argv[0]} <slack_channel> <slack_webhook> <run_mode>')
    sys.exit(1)
slack_channel = sys.argv[1]
slack_webhook = sys.argv[2]
run_mode = sys.argv[3]
if run_mode not in ['local', 'mixed', 'operator']:
    raise RuntimeError(f'Invalid run mode provided: {run_mode}')

# Initialize ray either on the cluster or locally otherwise.
if run_mode == 'operator':
    ray.init(address='auto')
else:
    ray.init()

# Start rayvens in operator mode.
rayvens.init(mode=run_mode)

# Create stream.
stream = rayvens.Stream('slack')


# Operator sub-task:
@ray.remote
def sub_task(context, intermediate_data):
    sub_task_outgoing_event = "sub-task " + intermediate_data
    print(sub_task_outgoing_event)
    context.publish(sub_task_outgoing_event)


# Operator task:
@ray.remote
def multi_part_task(context, incoming_event):
    print("multi-part-task:", incoming_event)
    for i in range(3):
        sub_task.remote(context, "sub-event" + str(i))


# Event sink config.
sink_config = dict(kind='slack-sink',
                   route='/toslack',
                   channel=slack_channel,
                   webhook_url=slack_webhook)

# Add sink to stream.
sink = stream.add_sink(sink_config)

stream.add_multi_operator(multi_part_task)

# Sends message to all sinks attached to this stream.
stream << f'Sending message to Slack sink in run mode {run_mode}.'

# Disconnect any sources or sinks attached to the stream 2 seconds after
# the stream is idle (i.e. no events were propagated by the stream).
stream.disconnect_all(after_idle_for=2)
