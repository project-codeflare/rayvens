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
import sys

# Receive message from stock price source and print it to console using the
# operator implementation.

# Initialize ray.
if len(sys.argv) < 2:
    print(f'usage: {sys.argv[0]} <run_mode>')
    sys.exit(1)
run_mode = sys.argv[1]

# TODO enable 'local', 'mixed.operator' modes.
if run_mode not in ['cluster.operator']:
    raise RuntimeError(f'Invalid run mode provided: {run_mode}')

# Initialize ray either on the cluster or locally otherwise.
if run_mode == 'cluster.operator':
    ray.init(address='auto')
else:
    ray.init()

# Start rayvens in the desired mode.
rayvens.init(mode=run_mode)

# Create stream.
stream = rayvens.create_stream('http')

# Event source config.
source_config = dict(
    kind='http-source',
    url='http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo',
    route='/from-http',
    period=3000)

# Attach source to stream.
source = stream.add_source.remote(source_config)

# Event source config.
another_source_config = dict(
    kind='http-source',
    url='http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo',
    route='/from-another-http',
    period=5000)

# Attach source to stream.
another_source = stream.add_source.remote(another_source_config)

# Wait for source to start.
stream.await_start.remote(source)
stream.await_start.remote(another_source)

# Log all events from stream-attached sources.
stream >> (lambda event: print('LOG:', event))

# Wait before ending program.
time.sleep(20)
