import ray
import rayvens

# this example demonstrate how to use a topic to connect
# event producers and consumers using a pub-sub pattern
#
# in this example, the event handlers are Ray actors
# the events are delivered to each actor in order
# but the interleaving of events across subscribers is arbitrary

# initialize ray
try:
    ray.init(address='auto')  # try to connect to cluster first
except ConnectionError:
    ray.init()  # fallback to local execution

# start rayvens client
client = rayvens.Client()

# create a topic actor
topic = client.create_topic('example')


# Ray actor to handle events
@ray.remote
class Accumulator:
    def __init__(self, name):
        self.name = name
        self.value = 0

    def add(self, delta):
        self.value += delta
        print(self.name, '=', self.value)


# create two actor instances
acc1 = Accumulator.remote('actor1')
acc2 = Accumulator.remote('actor2')

# subscribe actors to topic
topic.send_to.remote(acc1.add.remote)
topic.send_to.remote(acc2.add.remote)

# publish a few events
for i in range(10):
    topic.ingest.remote(i)
