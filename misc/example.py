import events
import os
import ray
from ray import serve
import time

ray.init()
client = serve.start()

source = events.Topic.remote('source')
sink = events.Topic.remote('sink')

source.subscribe.remote(sink.publish.remote)

events.post(sink, 'slack',
            f"slack:#kar-output?webhookUrl={os.environ['SLACK_WEBHOOK']}")

events.poll(client, source, 'http',
            'http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo')

# logger


@ray.remote
def log(data):
    print('LOG:', data)


source.subscribe.remote(log.remote)

time.sleep(60)
