import asyncio
import json
import ray
import rayvens

try:
    ray.init(address='auto')
except ConnectionError:
    ray.init(object_store_memory=78643200)

client = rayvens.Client()

source_config = dict(
    kind='http-source',
    url='http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo',
    period=3000)
source = client.create_topic('http', source=source_config)


@ray.remote
class Counter:
    def __init__(self):
        self.count = 0
        self.ready = asyncio.Event()

    def ingest(self, event):
        print('AAPL is', json.loads(event)[0]['price'])
        self.count += 1
        if self.count > 5:
            self.ready.set()

    async def wait(self):
        await self.ready.wait()


counter = Counter.remote()

source >> counter

ray.get(counter.wait.remote(), timeout=180)
