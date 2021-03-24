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

import asyncio
import json
import ray
import rayvens

# Initialize ray based on where ray will run inside the cluster using the
# kamel operator.
ray.init(address='auto')
run_mode = 'cluster.operator'


# Actor class for processing the events from the source.
@ray.remote
class Counter:
    def __init__(self):
        self.count = 0
        self.ready = asyncio.Event()

    def append(self, event):
        print('AAPL is', json.loads(event)[0]['price'])
        self.count += 1
        if self.count > 5:
            self.ready.set()

    async def wait(self):
        await self.ready.wait()


# Start the test.

# Start rayvens in the desired mode.
rayvens.init(mode=run_mode)

# Config for the source.
source_config = dict(
    kind='http-source',
    url='http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo',
    route='/test-from-http',
    period=3000)

# Create stream where we can attach sinks, sources and operators.
stream = rayvens.create_stream('http')

# Attach a source to the stream.
source = stream.add_source.remote(source_config)

# Instantiate the processor class for the events.
counter = Counter.remote()

# Await source to be ready.
ray.get(source)

# Send all events from the source to the processor.
stream >> counter

ray.get(counter.wait.remote(), timeout=180)
