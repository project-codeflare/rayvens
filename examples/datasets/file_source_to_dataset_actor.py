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
import json
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
                     events='CREATE')

# Run the source:
source = stream.add_source(source_config)


@ray.remote
class Filename:
    def __init__(self):
        self.filename = None

    def set_filename(self, event):
        print(f'received {len(event)} bytes')
        json_event = json.loads(event)
        print("Contents:")
        print("Filename:", json_event['filename'])
        print("Event type:", json_event['event_type'])
        self.filename = json_event['filename']

    def get_filename(self):
        return self.filename


# Instantiate actor.
filename_actor = Filename.remote()

# Process incoming file name.
stream >> filename_actor.set_filename

# Read JSON file to Ray dataset:
timeout_counter = 100
filename = None
while filename is None and timeout_counter > 0:
    filename = ray.get(filename_actor.get_filename.remote())
    timeout_counter -= 1
    time.sleep(1)
if filename is not None:
    ds = ray.experimental.data.read_json([filename])
    print(ds)
    print("Dataset constructed correctly")
else:
    print("No file was received")

# Run while events are still being received then stop if not.
stream.disconnect_all(after_idle_for=2)
