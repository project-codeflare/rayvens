import ray
import rayvens
import sys
import time

# Send message to Slack sink using the kamel anywhere operator implementation.

# Command line arguments:
if len(sys.argv) < 3:
    print(f'usage: {sys.argv[0]} <slack_channel> <slack_webhook>')
    sys.exit(1)
slack_channel = sys.argv[1]
slack_webhook = sys.argv[2]

# Initialize ray either on the cluster or locally otherwise.
try:
    ray.init(address='auto')
except ConnectionError:
    ray.init()

# Start rayvens client in operator mode.
client = rayvens.Client(camel_mode='operator')

# Create stream.
stream = client.create_stream('slack')

# Event sink config.
sink_config = dict(kind='slack-sink',
                   route='/toslack',
                   channel=slack_channel,
                   webhookUrl=slack_webhook)

# Add sink to stream.
sink = client.add_sink(stream, sink_config)

# Wait for sink to reach running state.
client.await_start(sink)

# Sends message to all sinks attached to this stream.
stream << "Use API in ANY_NODE mode by sending message to Slack sink."

time.sleep(5)
