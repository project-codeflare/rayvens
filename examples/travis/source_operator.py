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

try:
    ray.init(address='auto')
    camel_mode = 'operator'
except ConnectionError:
    ray.init(object_store_memory=78643200)
    camel_mode = 'local'

client = rayvens.Client(camel_mode=camel_mode)

source_config = dict(
    kind='http-source',
    url='http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo',
    period=3000)
source = client.create_stream('http', source=source_config)


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


counter = Counter.remote()

source >> counter

ray.get(counter.wait.remote(), timeout=180)
