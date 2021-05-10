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

import yaml


def http_source(config):
    if 'url' not in config:
        raise TypeError('Kind http-source requires a url.')
    url = config['url']
    period = config.get('period', 1000)
    return {'uri': f'timer:tick?period={period}', 'steps': [{'to': url}]}


def kafka_source(config):
    if 'topic' not in config:
        raise TypeError('Kind kafka-source requires a topic.')
    if 'broker' not in config:
        raise TypeError('Kind kafka-source requires a valid kafka broker.')
    topic = config['topic']
    kafka_broker = config['broker']
    return {'uri': f'kafka:{topic}?brokers={kafka_broker}', 'steps': []}


def generic_source(config):
    if 'spec' not in config:
        raise TypeError('Kind generic-source requires a spec.')
    if isinstance(config['spec'], str):
        return _process_generic_spec_str(config)

    # If the source spec is given as non-string we assume it is a valid
    # dictionary of the form:
    # {'uri':<uri_value>, 'steps':[<more yaml or empty>]}
    return config['spec']


sources = {
    'http-source': http_source,
    'kafka-source': kafka_source,
    'generic-source': generic_source
}


# construct a camel source specification from a rayvens source config
def construct_source(config, endpoint, inverted=False):
    if 'kind' not in config:
        raise TypeError('A Camel source needs a kind.')
    kind = config['kind']
    source_handler = sources.get(kind)
    if source_handler is None:
        raise TypeError(f'Unsupported Camel source: {kind}.')
    spec = source_handler(config)
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


def kafka_sink(config):
    if 'topic' not in config:
        raise TypeError('Kind kafka-sink requires a topic.')
    if 'broker' not in config:
        raise TypeError('Kind kafka-sink requires a valid kafka broker.')
    topic = config['topic']
    kafka_broker = config['broker']

    return {
        'steps': [{
            'to': f'kafka:{topic}?brokers={kafka_broker}',
        }]
    }


def test_sink(config):
    return {'steps': [{'log': {'message': "\"${body}\""}}]}


def generic_sink(config):
    if 'spec' not in config:
        raise TypeError('Kind generic-sink requires a spec.')
    if isinstance(config['spec'], str):
        return _process_generic_spec_str(config, sink=True)

    # If the sink spec is given as non-string we assume it is a valid
    # dictionary of the form:
    # {'uri':<uri_value>, 'steps':[<more yaml or empty>]}
    return config['spec']


sinks = {
    'slack-sink': slack_sink,
    'kafka-sink': kafka_sink,
    'generic-sink': generic_sink,
    'test-sink': test_sink
}


# construct a camel sink specification from a rayvens sink config
def construct_sink(config, endpoint):
    if 'kind' not in config:
        raise TypeError('A Camel sink needs a kind.')
    kind = config['kind']
    sink_handler = sinks.get(kind)
    if sink_handler is None:
        raise TypeError(f'Unsupported Camel sink: {kind}.')

    spec = sink_handler(config)
    spec['uri'] = endpoint
    spec = [{'from': spec}]
    return spec


def _process_generic_spec_str(config, sink=False):
    # Parse string to a Python dictionary.
    generic_spec = yaml.safe_load(config['spec'])

    # Ensure only a single source exists.
    # TODO: enable support for multi-source Yaml.
    if isinstance(generic_spec, list):
        if len(generic_spec) > 1:
            raise TypeError('Generic spec field has multiple sources.')
        generic_spec = generic_spec[0]

    # from will be inserted later.
    if 'from' in generic_spec:
        if generic_spec['from'] is None:
            del generic_spec['from']
        else:
            generic_spec = generic_spec['from']

    # A uri for the source must be present.
    if not sink and 'uri' not in generic_spec:
        raise TypeError('Generic spec needs a uri entry.')

    # A steps field is required but can be empty by default.
    if 'steps' not in generic_spec:
        generic_spec['steps'] = []

    return generic_spec
