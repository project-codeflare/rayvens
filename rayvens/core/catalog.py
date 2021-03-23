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


def http_source(config):
    if 'url' not in config:
        raise TypeError('Kind http-source requires a url.')
    url = config['url']
    period = config.get('period', 1000)
    return {'uri': f'timer:tick?period={period}', 'steps': [{'to': url}]}


def generic_source(config):
    if 'spec' not in config:
        raise TypeError('Kind generic-source requires a spec.')
    return config['spec']


sources = {'http-source': http_source, 'generic-source': generic_source}


# construct a camel source specification from a rayvens source config
def construct_source(config, endpoint, inverted=False):
    if 'kind' not in config:
        raise TypeError('A Camel source needs a kind.')
    kind = config['kind']
    f = sources.get(kind)
    if f is None:
        raise TypeError(f'Unsupported Camel source: {kind}.')
    spec = f(config)
    if inverted:
        spec['steps'].append({'bean': 'addToQueue'})
        spec = [{
            'from': spec
        }, {
            'from': {
                'uri': endpoint,
                'steps': [{
                    'bean': 'takeFromQueue'
                }]
            }
        }]
    else:
        spec['steps'].append({'to': endpoint})
        spec = [{'from': spec}]
    print(spec)
    return spec


def slack_sink(config):
    if 'channel' not in config:
        raise TypeError('Kind slack-sink requires a channel.')
    if 'webhookUrl' not in config:
        raise TypeError('Kind slack-sink requires a webhookUrl.')
    channel = config['channel']
    webhookUrl = config['webhookUrl']

    return {
        'steps': [{
            'to': f'slack:{channel}?webhookUrl={webhookUrl}',
        }]
    }


def generic_sink(config):
    if 'spec' not in config:
        raise TypeError('Kind generic-sink requires a spec.')
    return config['spec']


sinks = {'slack-sink': slack_sink, 'generic-sink': generic_sink}


# construct a camel sink specification from a rayvens sink config
def construct_sink(config, endpoint):
    if 'kind' not in config:
        raise TypeError('A Camel sink needs a kind.')
    kind = config['kind']
    f = sinks.get(kind)
    if f is None:
        raise TypeError(f'Unsupported Camel sink: {kind}.')

    spec = f(config)
    spec['uri'] = endpoint
    spec = [{'from': spec}]
    print(spec)
    return spec
