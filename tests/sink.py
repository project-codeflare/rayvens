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
import os

# Initialize ray based on where ray will run inside the cluster using the
# kamel operator.

# Default run mode.
run_mode = 'operator'
env_run_mode = os.getenv('RAYVENS_TEST_MODE')
if env_run_mode is not None:
    run_mode = env_run_mode

# Select appropriate Ray init method.
if run_mode == 'operator':
    ray.init(address='auto')
else:
    ray.init(object_store_memory=78643200)

# Start the test.

# Start rayvens in operator mode.
rayvens.init(mode=run_mode)

# Create stream.
stream = rayvens.Stream('test-sink')

# Event sink config.
test_sink_config = dict(kind='test-sink', route='/totestsink')

# Add sink to stream.
sink = stream.add_sink(test_sink_config)

# Sends message to all sinks attached to this stream.
output_message = f'Sending message to Slack sink in run mode {run_mode}.'
stream << output_message

# Verify outcome.
rayvens.meta(stream, 'verify_log', sink, output_message, wait_for_events=True)

# Delete all integrations from stream.
stream.disconnect_all(after_idle_for=5)
