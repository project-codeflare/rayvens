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

# This example demonstrates the use of Ray actors to handle events.
# The events are delivered to each actor in order. The processing order
# is therefore deterministic for each actor. But the interleaving of events
# across actors is arbitrary.

# initialize ray
ray.init()

# initialize rayvens
rayvens.init()

# create a stream
stream = rayvens.Stream('example')


# Ray actor to handle events
@ray.remote
class Accumulator:
    def __init__(self, name):
        self.name = name
        self.value = 0

    def append(self, delta):
        self.value += delta
        print(self.name, '=', self.value)


# create two actor instances
acc1 = Accumulator.remote('actor1')
acc2 = Accumulator.remote('actor2')

# subscribe actors to stream
stream >> acc1.append
stream >> acc2  # .append is implicit if no method name is provided

# publish a few events
for i in range(10):
    stream << i
