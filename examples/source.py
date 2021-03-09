import json
import ray
import rayvens
import time

# this example demonstrates how to subscribe to a Camel event source
# and process incoming events using a stateful actor

# initialize ray
try:
    ray.init(address='auto')  # try to connect to cluster first
except ConnectionError:
    ray.init()  # fallback to local execution

# start rayvens client
client = rayvens.Client()

# start event source
source_config = dict(
    kind='http-source',
    url='http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo',
    period=3000)
source = client.create_topic('http-source', source=source_config)

# log incoming events
source >> (lambda event: print('LOG:', event))


# Actor to compare APPL quote with last quote
@ray.remote
class Comparator:
    def __init__(self):
        self.last_quote = None

    def ingest(self, event):
        payload = json.loads(event)
        quote = payload[0]['price']  # payload[0] is AAPL
        try:
            if self.last_quote:
                if quote > self.last_quote:
                    print('AAPL is up')
                elif quote < self.last_quote:
                    print('AAPL is down')
                else:
                    print('AAPL is unchanged')
        finally:
            self.last_quote = quote


# comparator instance
comparator = Comparator.remote()

# subscribe comparator to source
source >> comparator

# run for a while
time.sleep(60)

# optionally disconnect source
client.disconnect(source)
