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

    def set_filename(self, filename):
        self.filename = filename

    def get_filename(self):
        return self.filename


filename_obj = Filename.remote()


def process_file(event, filename_obj):
    print(f'received {len(event)} bytes')
    json_event = json.loads(event)
    print("Contents:")
    print(json_event['filename'])
    print(json_event['event_type'])
    filename_obj.set_filename.remote(json_event['filename'])

    # filename = json_event['filename']
    # WARNING: Cannot pickle Ray itself so we cannot read a
    #          file using Datasets API in response to an event.
    # ds = ray.experimental.data.read_json([filename])
    # print(ds)


# Log object sizes to the console
stream >> (lambda event: process_file(event, filename_obj))

# Create a data set and write the csv file using datasets.
# TODO: Ray 1.5.1 uses pandas to write a CSV file so we avoid
#       using this method for writing CSV files.
# test_ds = ray.experimental.data.range(100)
# test_ds.write_csv("test_files/test.csv")

# # Write JSON file:
# with open('test_files/test.txt', 'w') as file:
#     json_data = {"greeting": "Hello!"}
#     json.dump(json_data, file)

# Read JSON file:
timeout_counter = 100
filename = ray.get(filename_obj.get_filename.remote())
while filename is None and timeout_counter > 0:
    filename = ray.get(filename_obj.get_filename.remote())
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
