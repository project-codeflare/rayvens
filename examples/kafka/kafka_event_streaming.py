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

# Event streaming from a third-party external source using Kafka.

# Command line arguments and validation:
if len(sys.argv) < 2:
    print(f'usage: {sys.argv[0]} <brokers> <password> <run_mode> OR'
          f'       {sys.argv[0]} <run_mode>')
    sys.exit(1)

# Brokers and run mode:
brokers = None
password = None
run_mode = sys.argv[1]
if len(sys.argv) == 4:
    brokers = sys.argv[1]
    password = sys.argv[2]
    run_mode = sys.argv[3]

if run_mode not in ['local', 'mixed', 'operator']:
    raise RuntimeError(f'Invalid run mode provided: {run_mode}')

# The Kafka topic used for communication.
topic = "externalTopic2"

# If using the Kafka broker started by Rayvens the following brokers
# are possible:
# - from inside the cluster: kafka:9092
# - from outside the cluster: localhost:31093
# If using a different Kafka service please provide the brokers in the
# form of host:port,host1:port1, ... .
if brokers is None:
    brokers = 'localhost:31093'
    if run_mode == 'operator':
        brokers = "kafka:9092"

# Initialize ray either on the cluster or locally otherwise.
if run_mode == 'operator':
    ray.init(address='auto')
else:
    ray.init()

# Start rayvens in operator mode."
rayvens.init(mode=run_mode, transport="kafka")

# Create stream.
stream = rayvens.Stream('http')

# Event source config.
source_config = dict(
    kind='http-source',
    url='https://query1.finance.yahoo.com/v7/finance/quote?symbols=AAPL',
    route='/from-http',
    period=3000,
    kafka_transport_topic=topic,
    kafka_transport_partitions=3)

# Attach source to stream.
source = stream.add_source(source_config)

# Log all events from stream-attached sources.
stream >> (lambda event: print('LOG:', event))

# Disconnect source after 10 seconds.
stream.disconnect_all(after=10)
