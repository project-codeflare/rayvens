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

# This example demonstrates the use of Ray tasks to handle events.
# These tasks are invoked in arbitrary order. The processing order
# is therefore non-deterministic.

# initialize ray
ray.init()

# initialize rayvens
rayvens.init()

# create a stream
stream = rayvens.Stream('example')


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
