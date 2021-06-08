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

# This example demonstrates how to receive events.

# Parse command-line arguments
if len(sys.argv) < 2:
    print(f'usage: {sys.argv[0]} <run_mode>')
    sys.exit(1)

# Check run mode:
run_mode = sys.argv[1]
if run_mode not in ['local', 'operator']:
    raise RuntimeError(f'Invalid run mode provided: {run_mode}')

# Initialize ray either on the cluster or locally otherwise.
if run_mode == 'operator':
    ray.init(address='auto')
else:
    ray.init()

# Start rayvens in the desired mode.
rayvens.init(mode=run_mode)

# Create an object stream:
stream = rayvens.Stream('bucket')

# Configure the source:
source_config = dict(kind='file-watch-source',
                     path='test_files',
                     events='DELETE,CREATE')

# Run the source:
source = stream.add_source(source_config)


def process_file(event):
    print(f'received {len(event)} bytes')
    print("Contents:")
    print(event)


# Log object sizes to the console
stream >> process_file

# Run for a while
time.sleep(100)
