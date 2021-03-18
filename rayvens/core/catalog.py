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


# construct a camel source specification from a rayvens source config
def construct_source(config, endpoint, inverted=False):
    if 'kind' not in config:
        raise TypeError('A Camel source needs a kind.')
    if config['kind'] not in ['http-source']:
        raise TypeError('Unsupported Camel source.')
    if 'url' not in config:
        raise TypeError('Kind http-source requires a url.')
    url = config['url']
    period = config.get('period', 1000)

    if inverted:
        return [{
            'from': {
                'uri': f'timer:tick?period={period}',
                'steps': [{
                    'to': url
                }, {
                    'bean': 'addToQueue'
                }]
            },
        }, {
            'from': {
                'uri': endpoint,
                'steps': [{
                    'bean': 'takeFromQueue'
                }]
            }
        }]

    return [{
        'from': {
            'uri': f'timer:tick?period={period}',
            'steps': [{
                'to': url
            }, {
                'to': endpoint
            }]
        }
    }]


# construct a camel sink specification from a rayvens sink config
def construct_sink(config, endpoint):
    if 'kind' not in config:
        raise TypeError('A Camel sink needs a kind.')
    if config['kind'] not in ['slack-sink']:
        raise TypeError('Unsupported Camel sink.')
    if 'channel' not in config:
        raise TypeError('Kind slack-sink requires a channel.')
    if 'webhookUrl' not in config:
        raise TypeError('Kind slack-sink requires a webhookUrl.')
    channel = config['channel']
    webhookUrl = config['webhookUrl']

    return [{
        'from': {
            'uri': endpoint,
            'steps': [{
                'to': f'slack:{channel}?webhookUrl={webhookUrl}',
            }]
        }
    }]
