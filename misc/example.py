import events
import os
import ray
from ray import serve
import time

ray.init()
client = serve.start()

# a topic to receive events from camel
source = events.Topic.remote('source')

# a topic to send events to camel
sink = events.Topic.remote('sink')

# an edge from source to sink
source.subscribe.remote(sink.publish.remote)

# configure and run camel sink
events.post(sink, 'slack',
            f"slack:#kar-output?webhookUrl={os.environ['SLACK_WEBHOOK']}")

# configure and run camel source
events.poll(client, source, 'http',
            'http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo')

# log events
source.subscribe.remote(lambda data: print('LOG:', data))

# run for a while
time.sleep(60)
