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
import json
import time

# Event streaming from a third-party external source using Kafka and
# dynamic subscribers.

# Command line arguments and validation:
if len(sys.argv) < 4:
    print(f'usage: {sys.argv[0]} <brokers> <password> <slack_channel>'
          '<slack_webhook> <run_mode> OR'
          f'       {sys.argv[0]} <slack_channel> <slack_webhook> <run_mode>')
    sys.exit(1)

# Brokers and run mode:
brokers = None
password = None
slack_channel = sys.argv[1]
slack_webhook = sys.argv[2]
run_mode = sys.argv[3]
if len(sys.argv) == 6:
    brokers = sys.argv[1]
    password = sys.argv[2]
    slack_channel = sys.argv[3]
    slack_webhook = sys.argv[4]
    run_mode = sys.argv[5]

if run_mode not in ['local', 'operator']:
    raise RuntimeError(f'Invalid run mode provided: {run_mode}')

# The Kafka topic used for communication.
topic = "partitionedTopic"

# Initialize ray either on the cluster or locally otherwise.
if run_mode == 'operator':
    ray.init(address='auto')
else:
    ray.init()

# Start rayvens in operator mode."
rayvens.init(mode=run_mode, transport="kafka")


@ray.remote
def process_currency_price(event):
    # Parse event:
    parsed_event = json.loads(event)

    # Extract currency name:
    currency = parsed_event['instrument'].split("/")[0]

    # Extract price:
    price = parsed_event['last']

    # Output latest currency price:
    print(f"{currency} : {price}")

    time.sleep(1)

    return f"{currency} : {price}"


# Create stream.
stream = rayvens.Stream('kafka-eventing', operator=process_currency_price)

# Event sink config.
sink_config = dict(kind='slack-sink',
                   channel=slack_channel,
                   webhookUrl=slack_webhook)

# Add sink to stream.
sink = stream.add_sink(sink_config)

# Event source config.
coins = ["BTC", "ETH"]
source_config = dict(kind='binance-source',
                     coin=coins,
                     period='500',
                     kafka_transport_topic=topic,
                     kafka_transport_partitions=3,
                     kafka_transport_static_subscribers=True)

# Attach source to stream.
source = stream.add_source(source_config)

# Disconnect source after 10 seconds.
stream.disconnect_all(after=10)
