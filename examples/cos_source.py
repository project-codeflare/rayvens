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

# This example demonstrates how to receive objects from AWS S3 or
# IBM Cloud Object Storage. It requires a bucket name, HMAC credentials,
# and the endpoint url. It simply pulls objects from the bucket and
# output the size of each object.
#
# WARNING: This example program deletes the objects from the bucket.

# Parse command-line arguments
if len(sys.argv) < 5:
    print(
        f'usage: {sys.argv[0]} <bucket> <access_key_id> <secret_access_key> <endpoint>'
    )
    sys.exit(1)
bucket = sys.argv[1]
access_key_id = sys.argv[2]
secret_access_key = sys.argv[3]
endpoint = sys.argv[4]

# Initialize Ray and Rayvens
ray.init()
rayvens.init()

# Create an object stream
stream = rayvens.Stream('bucket')

# Construct the URI for the S3 Camel source
uri = f'aws2-s3://{bucket}?accessKey={access_key_id}'
uri += f'&secretKey={secret_access_key}'
uri += f'&overrideEndpoint=true&uriEndpointOverride={endpoint}'

# Configure the source
source_config = dict(kind='generic-source', spec=f'uri: {uri}')

# Run the source
source = stream.add_source(source_config)

# Log object sizes to the console
stream >> (lambda event: print(f'received {len(event)} bytes'))

# Run for a while
time.sleep(60)
