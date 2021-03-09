import ray
import rayvens

# this example demonstrate how to use a topic to connect
# event producers and consumers using a pub-sub pattern
#
# in this example, the event handlers are simple functions
# they are invoked synchronously in order
# the processing order is therefore deterministic
# (within and across the two subscribers)

# initialize ray
try:
    ray.init(address='auto')  # try to connect to cluster first
except ConnectionError:
    ray.init(object_store_memory=78643200)  # fallback to local execution

# start rayvens client
client = rayvens.Client()

# create a topic actor
topic = client.create_topic('example')


# define a first event handler
def handler1(event):
    print('handler1 received', event)


# define a second event handler
def handler2(event):
    print('handler2 received', event)


# subscribe handlers to topic
topic >> handler1
topic >> handler2

# publish a few events
for i in range(10):
    topic << f'event {i}'
