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
from rayvens.core.verify import verify_log

# Initialize ray based on where ray will run inside the cluster using the
# kamel operator.
ray.init(address='auto')
run_mode = 'cluster.operator'

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

time.sleep(10)

# Verify outcome.
verify_log(sink, output_message)

# Delete all integrations from stream.
stream.disconnect_all()
