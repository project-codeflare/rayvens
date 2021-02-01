import ray
ray.init()

# Import events.
from events import topics

def subscribeResponseWithName(name="default"):
    print("Hello", name, "!")

# Create a topic as an actor.
newTopicHandle = topics.EventTopic.remote("newTopic")

# Add another subscriber this time with an argument.
newTopicHandle.subscribe.remote(subscribeResponseWithName)

# Print out the state of the EventTopic actor.
newTopicHandle.describe.remote()

# Publish with no arguments.
newTopicHandle.publish.remote()

# Publish with argument.
newTopicHandle.publish.remote("Doru")