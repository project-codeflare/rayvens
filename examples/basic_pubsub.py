import ray
ray.init()

# Import events.
from events import topics

# Set up subscriber responder.
def subscribeResponse():
  print("Hello publisher!")

# Create a topic as an actor.
newTopicHandle = topics.EventTopic.remote("newTopic")

# Add method as responder to any publication.
newTopicHandle.subscribe.remote(subscribeResponse)

# Print out the state of the EventTopic actor.
newTopicHandle.describe.remote()

# Publish with no arguments.
for i in range(10):
  newTopicHandle.publish.remote()