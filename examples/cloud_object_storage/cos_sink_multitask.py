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

# This example demonstrates how to send objects to the AWS S3 or
# IBM Cloud Object Storage.

# Parse command-line arguments
if len(sys.argv) < 5:
    print(f'usage: {sys.argv[0]} <bucket> <access_key_id> <secret_access_key>'
          '<endpoint> [<region>]')
    sys.exit(1)
bucket = sys.argv[1]
access_key_id = sys.argv[2]
secret_access_key = sys.argv[3]
endpoint = sys.argv[4]
region = None
if len(sys.argv) == 6:
    region = sys.argv[5]

# Initialize Ray and Rayvens
ray.init()

# TODO: make header setting work for Kafka transport. Currently the
# Camel-K component for Kafka does not propagate message headers. This
# will be fixed by Camel-K 1.8.0 release.
# rayvens.init(transport="kafka")
rayvens.init()

# Create an object stream
stream = rayvens.Stream('upload-file')

# Configure the sink
sink_config = dict(kind='cloud-object-storage-sink',
                   bucket_name=bucket,
                   access_key_id=access_key_id,
                   secret_access_key=secret_access_key,
                   endpoint=endpoint)

if region is not None:
    sink_config['region'] = region

# Run the sink
sink = stream.add_sink(sink_config)


# Operator sub-task:
@ray.remote
def sub_task(context, intermediate_data):
    contents = "sub-task " + intermediate_data
    print(contents)
    sub_task_outgoing_event = rayvens.OutputEvent(
        contents,
        {"CamelAwsS3Key": "custom_file_" + intermediate_data + ".json"})
    context.publish(sub_task_outgoing_event)


# Operator task:
@ray.remote
def multi_part_task(context, incoming_event):
    print("multi-part-task:", incoming_event)
    for i in range(3):
        sub_task.remote(context, str(i))


# Add multi-task operator to stream.
stream.add_multitask_operator(multi_part_task)

# Send file contents to Cloud Object Storage:
stream << "Random Event"

# Run for a while
time.sleep(10)
