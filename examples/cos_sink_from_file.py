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

# Configure the sink to upload a message from a file system file whenever
# the file is updated. The upload will consume (i.e. delete) the file unless
# the `keep_from_file` is set to True. The upload event is triggered
# automatically without any user intervention if the file is present initially
# or created/written after the sink is started.
file_to_sink_config = dict(kind='cloud-object-storage-sink',
                           name='sink-1',
                           bucket_name=bucket,
                           access_key_id=access_key_id,
                           secret_access_key=secret_access_key,
                           endpoint=endpoint,
                           from_file="test_files/test2.txt")

# Configure the sink to upload a message from a file system file
# in chunks of 2 MB whenever the file is updated. This sink can also
# upload, on demand, any other file system file which is provided by
# the user.
advanced_sink_config = dict(kind='cloud-object-storage-sink',
                            name='sink-2',
                            bucket_name=bucket,
                            access_key_id=access_key_id,
                            secret_access_key=secret_access_key,
                            endpoint=endpoint,
                            upload_type="multi-part",
                            part_size=2 * 1024 * 1024,
                            from_file="test_files/test3.txt")

if region is not None:
    advanced_sink_config['region'] = region
    file_to_sink_config['region'] = region

# Run the sink which gets automatically triggered whenever the `from_file`
# becomes available.
file_to_sink = stream.add_sink(file_to_sink_config)

# Run the more advanced sink which can do both the on demand uploads and the
# automatic uploads.
advanced_sink = stream.add_sink(advanced_sink_config)

# The on demand file upload will only reach the advanced_sink. The message
# for the other sink will be dropped as the automatically triggered sink
# cannot receive events directly from Rayvens.
if run_mode == "local":
    stream << Path("test_files/test.txt")

# This message type is not accepted by advanced_sink so it will not be sent
# to the advanced_sink.
stream << "Some other input which is invalid."

# Run for a while
time.sleep(30)
