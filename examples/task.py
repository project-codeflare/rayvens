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
import rayvens

# this example demonstrate how to use a stream to connect
# event producers and consumers using a pub-sub pattern
#
# in this example, the event handlers are Ray tasks
# they are invoked in arbitrary order
# (within and across the two subscribers)

try:
    ray.init(address='auto')  # try to connect to cluster first
except ConnectionError:
    ray.init()  # fallback to local execution

rayvens.init()

# create a stream actor
stream = rayvens.create_stream('example')


# define a first event handling task
@ray.remote
def handler1(event):
    print('handler1 received', event)


# define a second event handling task
@ray.remote
def handler2(event):
    print('handler2 received', event)


# subscribe tasks to stream
stream >> handler1
stream >> handler2

# publish a few events
for i in range(10):
    stream << f'event {i}'
