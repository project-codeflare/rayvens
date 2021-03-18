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

# Receive message from stock price source and print it to console using the
# operator implementation.

# Initialize ray.
try:
    ray.init(address='auto')  # try to connect to cluster first
except ConnectionError:
    ray.init()  # fallback to local execution

# Start rayvens client.
client = rayvens.Client(camel_mode='operator')

# Create stream.
stream = client.create_stream('http')

# Event source config.
source_config = dict(
    kind='http-source',
    url='http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo',
    period=3000)

# Attach source to stream.
source = client.add_source(stream, source_config)

# Wait for source to start.
client.await_start(source)

# Log all events from stream-attached sources.
stream >> (lambda event: print('LOG:', event))

# Wait before ending program.
time.sleep(10)
