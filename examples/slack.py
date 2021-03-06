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
source.subscribe.remote(lambda data: print('LOG:', data))

# start event sink actor
sink = client.Sink('slack', f'slack:#kar-output?webhookUrl={slack_webhook}')


@ray.remote
# Actor to compare stock quote with last quote and publish result
class Comparator:
    def __init__(self):
        self.lastQuote = None

    def compare(self, data):
        obj = json.loads(data)
        quote = obj[0]['price']
        if self.lastQuote:
            if quote > self.lastQuote:
                sink.publish.remote('UP')
            elif quote < self.lastQuote:
                sink.publish.remote('DOWN')
            else:
                sink.publish.remote('SAME')
        self.lastQuote = quote


# comparator instance
comparator = Comparator.remote()

# feed source events to comparator actor
source.subscribe.remote(comparator.compare.remote)

# run for a while
time.sleep(30)

# disconnect source and sink
client.disconnect(source)
client.disconnect(sink)

# wait for a while
time.sleep(20)
