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

import os
import ray
import rayvens

if os.getenv('RAYVENS_TEST_MODE') == 'local':
    ray.init(object_store_memory=78643200)
else:
    ray.init(address='auto')

rayvens.init()

stream = rayvens.Stream('example')


def handler1(event):
    print('handler1 received', event)


def handler2(event):
    print('handler2 received', event)


stream >> handler1
stream >> handler2

for i in range(10):
    stream << f'event {i}'
