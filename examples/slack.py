import json
import ray
import rayvens
import sys
import time

# this example demonstrates how to use Camel
# to receive and emit external events
#
# fetch AAPL quotes every 3 seconds
# analyze trend (up/down/same)
# publish trend to slack
#
# http-cron event source -> comparator actor -> slack event sink
#
# app requires a single command line argument: the slack webhook

# process command line arguments
if len(sys.argv) < 2:
    print(f'usage: {sys.argv[0]} <slack_webhook>')
    sys.exit(1)
slack_webhook = sys.argv[1]

# initialize ray
try:
    ray.init(address='auto')  # try to connect to cluster first
except ConnectionError:
    ray.init()  # fallback to local execution

# start rayvens client
client = rayvens.Client()

# start event source actor
url = 'http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo'
source = client.create_topic('http-cron', source=dict(url=url, period=3000))

# log incoming events
source >> (lambda event: print('LOG:', event))

# start event sink actor
sink = client.create_topic(
    'slack', sink=f'slack:#kar-output?webhookUrl={slack_webhook}')


@ray.remote
# Actor to compare stock quote with last quote
class Comparator:
    def __init__(self):
        self.lastQuote = None

    def ingest(self, event):
        payload = json.loads(event)
        quote = payload[0]['price']
        try:
            if self.lastQuote:
                if quote > self.lastQuote:
                    return 'AAPL is up'
                elif quote < self.lastQuote:
                    return 'AAPL is down'
                else:
                    return 'AAPL is unchanged'
        finally:
            self.lastQuote = quote


# comparator instance
comparator = Comparator.remote()

# stream operator applying comparator to events
operator = client.create_topic('comparator', operator=comparator)

# connect source to comparator to sink
source >> operator >> sink

# run for a while
time.sleep(60)

# optionally disconnect source and sink
client.disconnect(source)
client.disconnect(sink)
