import ray
import rayvens
import time

# Receive message from stock price source and print it to console using the
# operator implementation.

# Initialize ray.
try:
    ray.init(address='auto')  # try to connect to cluster first
except ConnectionError:
    ray.init()  # fallback to local execution

# Start rayvens client.
client = rayvens.Client(camel_mode='operator')

# Start event source.
source_config = dict(
    kind='http-source',
    url='http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo',
    period=3000)
source = client.create_topic('http', source=source_config)

# Log incoming events
source >> (lambda event: print('LOG:', event))

# Wait before ending program.
time.sleep(300)
