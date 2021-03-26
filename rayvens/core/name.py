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

import re


# name if provided else kind
def name_source(config):
    if 'kind' not in config:
        raise TypeError('A Camel source needs a kind.')
    return config.get('name', config['kind'])


# name if provided else kind
def name_sink(config):
    if 'kind' not in config:
        raise TypeError('A Camel sink needs a kind.')
    return config.get('name', config['kind'])


# sanitize name for use as Kubernetes name and file name
def sanitize(name):
    name = str(name)
    name = name.lower()
    name = re.sub('[^a-z0-9]', '-', name)
    name = re.sub('-{2,}', '-', name)
    name = name[-253:]
    name = name.strip('-')
    return name


# combine stream name and source/sink name
def name_integration(stream_name, name_or_kind):
    return sanitize(stream_name + '-' + name_or_kind)
