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
# http-source -> comparator actor -> slack-sink

# process command line arguments
if len(sys.argv) < 3:
    print(f'usage: {sys.argv[0]} <slack_channel> <slack_webhook>')
    sys.exit(1)
slack_channel = sys.argv[1]
slack_webhook = sys.argv[2]

# initialize ray
try:
    ray.init(address='auto')  # try to connect to cluster first
except ConnectionError:
    ray.init()  # fallback to local execution

# start rayvens client
client = rayvens.Client()

# start event source actor
source_config = dict(
    kind='http-source',
    url='http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo',
    period=3000)
source = client.create_topic('http-source', source=source_config)

# log incoming events
source >> (lambda event: print('LOG:', event))

# start event sink actor
sink_config = dict(kind='slack-sink',
                   channel=slack_channel,
                   webhookUrl=slack_webhook)
sink = client.create_topic('slack', sink=sink_config)


# Actor to compare APPL quote with last quote
@ray.remote
class Comparator:
    def __init__(self):
        self.last_quote = None

    def ingest(self, event):
        payload = json.loads(event)  # parse event string to json
        quote = payload[0]['price']  # payload[0] is AAPL
        try:
            if self.last_quote:
                if quote > self.last_quote:
                    return 'AAPL is up'
                elif quote < self.last_quote:
                    return 'AAPL is down'
                else:
                    return 'AAPL is unchanged'
        finally:
            self.last_quote = quote


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
