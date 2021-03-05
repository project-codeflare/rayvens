import rayvens
import json
import ray
import sys
import time

# fetch AAPL quotes every 3 seconds, analyze trend (up/down/same), and publish
# trend to slack
#
# the flow of events is:
#     http-cron camel source -> incoming topic -> comparator actor -> outgoing
# topic -> slack camel sink
#
# app requires a single command line argument: the slack webhook

# process command line arguments
if len(sys.argv) < 2:
    print(f'usage: {sys.argv[0]} <slack_webhook>')
    sys.exit(1)
slack_webhook = sys.argv[1]

# initialize ray
try:
    ray.init(address='auto')
except ConnectionError:
    ray.init(resources={'camel': 1})

# start rayvens
camel = rayvens.Camel.remote()

# a topic to receive events from
incoming = rayvens.Topic.remote('source')

# log incoming events
incoming.subscribe.remote(lambda data: print('LOG:', data))

# a topic to send events to camel
outgoing = rayvens.Topic.remote('sink')


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
                outgoing.publish.remote('UP')
            elif quote < self.lastQuote:
                outgoing.publish.remote('DOWN')
            else:
                outgoing.publish.remote('SAME')
        self.lastQuote = quote


# comparator instance
comparator = Comparator.remote()

# feed incoming events to comparator actor
incoming.subscribe.remote(comparator.compare.remote)

# configure and run camel sink to publish to slack
camel.addSink.remote('slack', outgoing,
                     f'slack:#kar-output?webhookUrl={slack_webhook}')

# configure and run camel source to fetch AAPL price periodically
camel.addSource.remote(
    'http-cron',
    incoming,
    'http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo',
    period=3000)

# run for a while
time.sleep(20)

# terminate camel integrations and disconnect subscribers
camel.disconnectAll.remote(incoming)
camel.disconnectAll.remote(outgoing)

# wait for a while
time.sleep(20)
