import ray
ray.init()

# Import events.
from events import topics

@ray.remote
def subscribeEnglishWithName(name="default"):
    print("Hello", name, "!")

@ray.remote
def subscribeFrenchWithName(name="default"):
    print("Bonjour", name, "!")

@ray.remote
def subscribeRomanianWithName(name="default"):
    print("Buna", name, "!")

# Create a topic as an actor.
newTopicHandle = topics.EventTopic.remote("newTopic")

# Add another subscriber this time with an argument.
newTopicHandle.subscribe.remote(subscribeEnglishWithName)
newTopicHandle.subscribe.remote(subscribeFrenchWithName)
newTopicHandle.subscribe.remote(subscribeRomanianWithName)

# Print out the state of the EventTopic actor.
newTopicHandle.describe.remote()

# Publish with no arguments.
newTopicHandle.publishToRemote.remote()

# Publish with argument.
for i in range(10):
    newTopicHandle.publishToRemote.remote("Doru %s" % i)