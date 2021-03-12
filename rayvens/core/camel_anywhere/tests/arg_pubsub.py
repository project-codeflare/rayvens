from rayvens.core.camel_anywhere import topics
import ray
ray.init()

# Import events.


def subscribeEnglishWithName(name="default"):
    print("Hello", name, "!")


def subscribeFrenchWithName(name="default"):
    print("Bonjour", name, "!")


def subscribeRomanianWithName(name="default"):
    print("Buna", name, "!")


print("Start greetings!")

# Create a topic as an actor.
newTopicHandle = topics.EventTopic.remote("newTopic")

# Add subscribers.
newTopicHandle.subscribe.remote(subscribeEnglishWithName)
newTopicHandle.subscribe.remote(subscribeFrenchWithName)
newTopicHandle.subscribe.remote(subscribeRomanianWithName)

# Print out the state of the EventTopic actor.
newTopicHandle.describe.remote()

# Publish with no arguments.
newTopicHandle.publish.remote()

# Publish with argument.
for i in range(10):
    newTopicHandle.publish.remote("Doru %s" % i)
