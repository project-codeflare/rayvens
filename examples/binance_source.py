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
import json

# Source for coin prices.

# Initialize ray.
if len(sys.argv) < 2:
    print(f'usage: {sys.argv[0]} <run_mode>')
    sys.exit(1)
run_mode = sys.argv[1]

if run_mode not in ['local', 'operator']:
    raise RuntimeError(f'Invalid run mode provided: {run_mode}')

# Initialize ray either on the cluster or locally otherwise.
if run_mode == 'operator':
    ray.init(address='auto')
else:
    ray.init()

# Start rayvens in the desired mode.
rayvens.init(mode=run_mode)

# Establish an existing portfolio.
coins = ["BTC", "ETH"]

# Create stream.
stream = rayvens.Stream('crypto')

# Event source config.
source_config = dict(kind='binance-source', coin=coins, period='3000')

# Attach source to stream.
source = stream.add_source(source_config)


def process_message(event):
    # Parse event:
    parsed_event = json.loads(event)

    # Extract currency name:
    currency = parsed_event['currencyPair'].split("/")[0]

    # Extract price:
    price = parsed_event['last']

    # Output latest currency price:
    print(f"{currency} : {price}")


# Send message to processor.
stream >> process_message

# Wait before ending program.
time.sleep(20)

stream.disconnect_all()
