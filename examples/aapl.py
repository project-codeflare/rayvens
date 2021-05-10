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
import sys
import time

# This example demonstrates how to use Camel
# to receive and emit external events.
#
# fetch AAPL quotes every 3 seconds
# analyze trend (up/down/stable)
# publish trend to slack
#
# http source -> comparator actor -> slack sink

# process command line arguments
if len(sys.argv) != 3 and len(sys.argv) != 1:
    print(f'usage: {sys.argv[0]} [<slack_channel> <slack_webhook>]')
    sys.exit(1)
slack_channel = sys.argv[1] if len(sys.argv) == 3 else ''
slack_webhook = sys.argv[2] if len(sys.argv) == 3 else ''

# initialize ray
ray.init()

# initialize rayvens
rayvens.init()

# create a source stream
source_config = dict(
    kind='http-source',
    url='http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo',
    period=3000)
source = rayvens.Stream('http', source_config=source_config)

# log incoming events
source >> (lambda event: print('LOG:', event))

if slack_channel != '':
    # create a sink stream
    sink_config = dict(kind='slack-sink',
                       channel=slack_channel,
                       webhookUrl=slack_webhook)
    sink = rayvens.Stream('slack', sink_config=sink_config)

    # actor to compare APPL quote with last quote
    @ray.remote
    class Comparator:
        def __init__(self):
            self.last_quote = None

        def append(self, event):
            payload = json.loads(event)  # parse event payload to json
            quote = payload[0]['price']  # extract AAPL quote
            if self.last_quote:
                if quote > self.last_quote:
                    sink.append('AAPL is up')
                elif quote < self.last_quote:
                    sink.append('AAPL is down')
                else:
                    sink.append('AAPL is stable')
            self.last_quote = quote

    comparator = Comparator.remote()  # instantiate comparator actor
    source.send_to(comparator)  # subscribe comparator to source

# run for a while
time.sleep(120)
