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

# This example demonstrates how to create a stream of events,
# subscribe to this stream, and append events to the stream.

# initialize ray
ray.init()

# initialize rayvens
rayvens.init()

# create a stream
stream = rayvens.Stream('example')

# deliver all future events to print
stream >> print

# append two events to the stream in order
stream << 'hello' << 'world'
