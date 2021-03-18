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
