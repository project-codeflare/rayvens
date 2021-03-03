import events
import os
import ray
from ray import serve
import sys
import time

# process command line arguments
if len(sys.argv) < 2:
    print(f'{sys.argv[0]} <slack_webhook>')
    sys.exit(1)
slack_webhook = sys.argv[1]

# initialize ray
try:
    ray.init(address="auto")
    in_cluster = True
except ConnectionError:
    ray.init()
    in_cluster = False

client = serve.start(http_options={'host': '0.0.0.0',
                                   'location': 'EveryNode'})

# a topic to receive events from camel
source = events.Topic.remote('source')

# a topic to send events to camel
sink = events.Topic.remote('sink')

# an edge from source to sink
source.subscribe.remote(sink.publish.remote)

# configure and run camel sink
events.post(in_cluster, sink, 'slack',
            f'slack:#kar-output?webhookUrl={slack_webhook}')

# configure and run camel source
events.poll(in_cluster, client, source, 'http',
            'http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo')

# log events
source.subscribe.remote(lambda data: print('LOG:', data))

# run for a while
time.sleep(20)

# terminate camel integrations and disconnect subscribers
events.disconnect(source)
events.disconnect(sink)

# wait for a while
time.sleep(20)
