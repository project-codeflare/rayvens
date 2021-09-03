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

import os
import ray
import rayvens

# Initialize run mode.
run_mode = 'operator'
env_run_mode = os.getenv('RAYVENS_TEST_MODE')
if env_run_mode is not None:
    run_mode = env_run_mode

if run_mode == 'operator':
    ray.init(address='auto')
else:
    ray.init(object_store_memory=78643200)

# The Kafka topic used for communication.
topic = "testTopic"

rayvens.init(mode=run_mode, transport='kafka')

# Create source stream and configuration.
source_stream = rayvens.Stream('kafka-source-stream')

# Event sink config.
test_sink_config = dict(kind='test-sink')

# Add sink to stream.
test_sink = source_stream.add_sink(test_sink_config)

source_config = dict(
    kind='http-source',
    url='https://query1.finance.yahoo.com/v7/finance/quote?symbols=AAPL',
    route='/from-http',
    period=2000)
source = source_stream.add_source(source_config)

# Verify outcome.
source_stream._meta('verify_log', test_sink, "quoteResponse")

# Disconnect source and sink.
source_stream.disconnect_all(after=10)
