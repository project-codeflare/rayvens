import rayvens
import json
import ray
import sys
import time

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
source = client.Source(
    'http-cron',
    'http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo',
    period=3000)

# log incoming events
source.subscribe.remote(lambda event: print('LOG:', event))

# start event sink actor
sink = client.Sink('slack', f'slack:#kar-output?webhookUrl={slack_webhook}')


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
                    return 'UP'
                elif quote < self.lastQuote:
                    return 'DOWN'
                else:
                    return 'SAME'
        finally:
            self.lastQuote = quote


# comparator instance
comparator = Comparator.remote()

# process event stream using comparator
operator = client.Operator('comparator', comparator.compare.remote)
source.subscribe.remote(operator.publish.remote)
operator.subscribe.remote(sink.publish.remote)

# or without creating a separate operator
# sink.add_operator.remote(comparator.compare.remote)
# source.subscribe.remote(sink.publish.remote)

# run for a while
time.sleep(60)

# optionally disconnect source and sink
client.disconnect(source)
client.disconnect(sink)
