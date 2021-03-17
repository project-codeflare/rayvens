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

# Create stream.
stream = client.create_stream('http')

# Event source config.
source_config = dict(
    kind='http-source',
    url='http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo',
    period=3000)

# Attach source to stream.
source = client.add_source(stream, source_config)

# Wait for source to start.
client.await_start(source)

# Log all events from stream-attached sources.
stream >> (lambda event: print('LOG:', event))

# Wait before ending program.
time.sleep(10)
