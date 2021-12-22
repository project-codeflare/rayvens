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
import sys
import ray
import rayvens

# Initialize run mode.
if len(sys.argv) < 2:
    run_mode = 'local'
else:
    run_mode = sys.argv[1]

if os.getenv('RAYVENS_TEST_MODE') == 'local':
    ray.init(object_store_memory=78643200)
else:
    ray.init(address='auto')

# The Kafka topic used for communication.
topic = "testTopicPartitioned"

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
    period=2000,
    kafka_transport_topic=topic,
    kafka_transport_partitions=3)
source = source_stream.add_source(source_config)

# Verify outcome. Since events are going through the Kafka infrastructure
# we need to disable checks based on event counts.
rayvens.meta(source_stream,
             'verify_log',
             test_sink,
             "quoteResponse",
             wait_for_events=False)

# Disconnect source and sink.
source_stream.disconnect_all(after=10)
