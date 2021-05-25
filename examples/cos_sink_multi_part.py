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
from pathlib import Path

# This example demonstrates how to send objects to the AWS S3 or
# IBM Cloud Object Storage using multi-part uploads.

# Parse command-line arguments
if len(sys.argv) < 7:
    print(f'usage: {sys.argv[0]} <bucket> <access_key_id> <secret_access_key>'
          '<endpoint> <region> <run_mode>')
    sys.exit(1)
bucket = sys.argv[1]
access_key_id = sys.argv[2]
secret_access_key = sys.argv[3]
endpoint = sys.argv[4]
region = sys.argv[5]
run_mode = sys.argv[6]

# Initialize Ray and Rayvens
if run_mode not in ['local', 'operator']:
    raise RuntimeError(f'Invalid run mode provided: {run_mode}')

# Initialize ray either on the cluster or locally otherwise.
if run_mode == 'operator':
    ray.init(address='auto')
else:
    ray.init()

# Start rayvens in the desired mode.
rayvens.init(mode=run_mode)

# Create an object stream
stream = rayvens.Stream('upload-file')

# Configure the source to upload a message in 2 MB chunks
sink_config = dict(kind='cloud-object-storage-sink',
                   bucket_name=bucket,
                   access_key_id=access_key_id,
                   secret_access_key=secret_access_key,
                   endpoint=endpoint,
                   upload_type="multi-part",
                   part_size=2 * 1024 * 1024)

if region is not None:
    sink_config['region'] = region

# Run the sink
sink = stream.add_sink(sink_config)

# Local:
if run_mode == "local":
    stream << Path("test_files/test.txt")

# TODO: add cluster file.

# Run for a while
time.sleep(20)
