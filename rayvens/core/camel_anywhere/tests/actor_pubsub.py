#
# Copyright IBM Corporation 2021
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from rayvens.core.camel_anywhere import topics
import ray
ray.init()

# Import events.


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
