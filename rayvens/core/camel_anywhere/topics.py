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

import ray


@ray.remote
class EventTopic(object):
    def __init__(self, name):
        self.name = name
        self.subscribers = []

    def subscribe(self, subscriberFunction):
        self.subscribers.append(subscriberFunction)

    def publish(self, *args, **kwargs):
        for subscriberFunction in self.subscribers:
            subscriberFunction(*args, **kwargs)

    def publishToRemote(self, *args, **kwargs):
        for subscriberFunction in self.subscribers:
            subscriberFunction.remote(*args, **kwargs)

    def describe(self):
        print("Topic name:", self.name)
        print("Number of subscribers:", len(self.subscribers))
