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

import json
import ray
import rayvens
import time

# This example demonstrates how to subscribe to a Camel event source
# and process incoming events using a Ray actor.

# initialize ray
ray.init()

# initialize rayvens
rayvens.init()

# create a source stream
source_config = dict(
    kind='http-source',
    url='https://query1.finance.yahoo.com/v7/finance/quote?symbols=AAPL',
    period=3000)
source = rayvens.Stream('http', source_config=source_config)

# log incoming events
source >> (lambda event: print('LOG:', event))


# actor to compare APPL quote with last quote
@ray.remote
class Comparator:
    def __init__(self):
        self.last_quote = None

    def append(self, event):
        payload = json.loads(event)  # parse event string to json
        quote = payload['quoteResponse']['result'][0]['regularMarketPrice']
        try:
            if self.last_quote:
                if quote > self.last_quote:
                    print('AAPL is up')
                elif quote < self.last_quote:
                    print('AAPL is down')
                else:
                    print('AAPL is stable')
        finally:
            self.last_quote = quote


# comparator instance
comparator = Comparator.remote()

# subscribe comparator to source
source >> comparator

# run for a while
time.sleep(120)
