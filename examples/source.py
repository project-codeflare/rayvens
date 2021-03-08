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

# start event source actor
source = client.Source(
    'http-cron',
    'http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo',
    period=3000)

# log incoming events
source.subscribe.remote(lambda event: print('LOG:', event))


@ray.remote
# Actor to compare stock quote with last quote
class Comparator:
    def __init__(self):
        self.lastQuote = None

    def compare(self, event):
        payload = json.loads(event)
        quote = payload[0]['price']
        try:
            if self.lastQuote:
                if quote > self.lastQuote:
                    print('AAPL is up')
                elif quote < self.lastQuote:
                    print('AAPL is down')
                else:
                    print('AAPL is unchanged')
        finally:
            self.lastQuote = quote


# comparator instance
comparator = Comparator.remote()

# create stream operator from comparator
operator = client.Operator('comparator', comparator.compare.remote)

# subscribe operator to source
source.subscribe.remote(operator.publish.remote)

# run for a while
time.sleep(60)

# optionally disconnect source and sink
client.disconnect(source)
