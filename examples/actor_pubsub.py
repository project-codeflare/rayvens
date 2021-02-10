import ray
ray.init()

# Import events.
from events import topics

@ray.remote
class EnglishSubscriber(object):
    def __init__(self):
        self.greeting = "Hello"

    def greet(self, name="default"):
        print(self.greeting, name, "!")

@ray.remote
class FrenchSubscriber(object):
    def __init__(self):
        self.greeting = "Bonjour"

    def greeting(self, name="default"):
        print(self.greeting, name, "!")

@ray.remote
class RomanianSubscriber(object):
    def __init__(self):
        self.greeting = "Buna"

    def sayhi(self, name="default"):
        print(self.greeting, name, "!")

# Create a topic as an actor.
newTopicHandle = topics.EventTopic.remote("newTopic")

# Create actor greeters.
newEnglishActor = EnglishSubscriber.remote()
newFrenchActor = FrenchSubscriber.remote()
newRomanianActor = RomanianSubscriber.remote()

# Add subscribers.
newTopicHandle.subscribe.remote(newEnglishActor.greet)
newTopicHandle.subscribe.remote(newFrenchActor.greeting)
newTopicHandle.subscribe.remote(newRomanianActor.sayhi)

# Print out the state of the EventTopic actor.
newTopicHandle.describe.remote()

# Publish with no arguments.
newTopicHandle.publishToRemote.remote()

# Publish with argument.
for i in range(10):
    newTopicHandle.publishToRemote.remote("Doru %s" % i)