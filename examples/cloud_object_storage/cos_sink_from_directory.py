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

# Configure the sink to upload a message from a file system directory whenever
# a new file is dumped inside the directory. The upload will consume (i.e.
# delete) the file unless the `keep_file` is set to True. The upload event is
# triggered automatically without any user intervention.
dir_to_sink_config = dict(kind='cloud-object-storage-sink',
                          name='sink',
                          bucket_name=bucket,
                          access_key_id=access_key_id,
                          secret_access_key=secret_access_key,
                          endpoint=endpoint,
                          from_directory="test_files_copy/")

if region is not None:
    dir_to_sink_config['region'] = region

# Run the sink which gets automatically triggered whenever a file is dumped in
# the monitored file system directory.
dir_to_sink = stream.add_sink(dir_to_sink_config)

# stream._meta('verify_log', dir_to_sink, "BLA")

# Run for a while to give a chance for files to be dropped inside the directory
time.sleep(100)
