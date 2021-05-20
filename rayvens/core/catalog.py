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


def _kafka_SASL_uri(topic, kafka_brokers, password):
    security_protocol = 'SASL_SSL'
    username = "token"
    conf = 'org.apache.kafka.common.security.plain.PlainLoginModule' \
           f' required username=\"{username}\" password=\"{password}\";'
    uri = f'kafka:{topic}?brokers={kafka_brokers}' \
          f'&securityProtocol={security_protocol}' \
          f'&saslMechanism=PLAIN' \
          f'&saslJaasConfig={conf}' \
          f'&sslKeyPassword={password}'
    return uri


def kafka_source(config):
    if 'topic' not in config:
        raise TypeError('Kind kafka-source requires a topic.')
    if 'brokers' not in config:
        raise TypeError('Kind kafka-source requires a valid kafka broker.')
    topic = config['topic']
    kafka_brokers = config['brokers']
    uri = f'kafka:{topic}?brokers={kafka_brokers}'
    if 'SASL_password' in config:
        uri = _kafka_SASL_uri(topic, kafka_brokers, config['SASL_password'])
    return {'uri': uri, 'steps': []}


def telegram_source(config):
    if 'authorization_token' not in config:
        raise TypeError('Telegram source requires an authorization token.')
    authorization_token = config['authorization_token']
    return {
        'uri': f'telegram:bots?authorizationToken={authorization_token}',
        'steps': [{
            'marshal': {
                'json': {}
            }
        }]
    }


def _binance_route(period, coin):
    return {
        'uri':
        f"timer:update?period={period}",
        'steps': [{
            'to':
            "xchange:binance?service=marketdata&method=ticker&"
            f"currencyPair={coin}/USDT"
        }, {
            'marshal': {
                'json': {}
            }
        }]
    }


def binance_source(config):
    if 'coin' not in config:
        raise TypeError(
            'Crypto source requires the official cryptocurrency symbol'
            '(example, for Bitcoin the symbol is BTC).')
    coin = config['coin']
    period = 3000
    if 'period' in config:
        period = config['period']

    if isinstance(coin, list):
        routes = []
        for coin_id in coin:
            routes.append(_binance_route(period, coin_id))
        return routes

    return _binance_route(period, coin)


def cos_source(config):
    if 'bucket_name' not in config:
        raise TypeError('Cloud object storage source requires a bucket name.')
    if 'access_key_id' not in config:
        raise TypeError(
            'Cloud object storage source requires an access key id.')
    if 'secret_access_key' not in config:
        raise TypeError(
            'Cloud object storage source requires an secret access key.')
    if 'endpoint' not in config:
        raise TypeError('Cloud object storage source requires an endpoint.')
    bucket_name = config['bucket_name']
    access_key_id = config['access_key_id']
    secret_access_key = config['secret_access_key']
    endpoint = config['endpoint']

    # Ensure this is a valid, supported endpoint:
    split_endpoint = _parse_endpoint(endpoint)

    # Resolve region:
    region = 'us-east'
    if 'region' in config:
        region = config['region']
    else:
        region = split_endpoint[1]

    # Assemble URI:
    uri = f'aws2-s3://{bucket_name}?accessKey={access_key_id}' \
          f'&secretKey={secret_access_key}' \
          '&overrideEndpoint=true' \
          f'&uriEndpointOverride={endpoint}' \
          f'&region={region}'
    return {'uri': uri, 'steps': []}


def generic_source(config):
    if 'spec' in config:
        spec = config['spec']
        if isinstance(config['spec'], str):
            spec = _process_generic_spec_str(config)
    elif 'uri' in config:
        # A source URI has been passed in, incorporate it in the generic
        # source YAML.
        spec = {'uri': config['uri'], 'steps': []}
    else:
        raise TypeError('Kind generic-source requires a spec or a uri field.')

    # If the source spec is given as non-string we assume it is a valid
    # dictionary of the form:
    # {'uri':<uri_value>, 'steps':[<more yaml or empty>]}
    if 'uri' not in spec:
        raise TypeError('Generic source requires a uri.')
    if 'steps' not in spec:
        raise TypeError('Steps field missing.')

    return spec


def generic_periodic_source(config):
    period = config.get('period', 1000)

    if 'spec' in config:
        # Parse string config if present otherwise spec is config:
        spec = config['spec']
        if isinstance(config['spec'], str):
            spec = _process_generic_spec_str(config)
    elif 'uri' in config:
        spec = {'uri': config['uri'], 'steps': []}
    else:
        raise TypeError('Kind generic-source requires a spec or a uri field.')

    # The target uri is the uri we will periodically poll.
    if 'uri' not in spec:
        raise TypeError('Periodic generic source requires a uri.')
    target_uri = spec['uri']

    periodic_spec = {
        'uri': f'timer:tick?period={period}',
        'steps': [{
            'to': target_uri
        }]
    }

    # Append any additional steps:
    periodic_spec['remaining_steps'] = spec['steps']

    return periodic_spec


sources = {
    'http-source': http_source,
    'kafka-source': kafka_source,
    'telegram-source': telegram_source,
    'binance-source': binance_source,
    'cloud-object-storage-source': cos_source,
    'generic-source': generic_source,
    'generic-periodic-source': generic_periodic_source
}


def _finalize_route(spec, endpoint, inverted):
    if inverted:
        spec['steps'].append({'bean': 'addToQueue'})
    else:
        spec['steps'].append({'to': endpoint})
    spec = [{'from': spec}]
    return spec


# construct a camel source specification from a rayvens source config
def construct_source(config, endpoint, inverted=False):
    if 'kind' not in config:
        raise TypeError('A Camel source needs a kind.')
    kind = config['kind']
    source_handler = sources.get(kind)
    if source_handler is None:
        raise TypeError(f'Unsupported Camel source: {kind}.')

    spec = source_handler(config)

    # Extract remaining steps if any:
    remaining_steps = None
    if 'remaining_steps' in spec:
        remaining_steps = spec['remaining_steps']
        del spec['remaining_steps']

    # Multi-source integration with several routes:
    if isinstance(spec, list):
        # Generic sources do now allow multiple routes:
        if remaining_steps is not None:
            raise TypeError(
                'Generic source with multiple routes not supported')

        spec_list = []
        for spec_entry in spec:
            spec_list.extend(_finalize_route(spec_entry, endpoint, inverted))
        if inverted:
            spec_list.append({
                'from': {
                    'uri': endpoint,
                    'steps': [{
                        'bean': 'takeFromQueue'
                    }]
                }
            })
        return spec_list

    # Regular integration with only one route:
    spec = _finalize_route(spec, endpoint, inverted)
    if inverted:
        # Route fetching from queue:
        from_queue = {
            'from': {
                'uri': endpoint,
                'steps': [{
                    'bean': 'takeFromQueue'
                }]
            }
        }

        # Attach remaining steps after fetching from the queue.
        if remaining_steps is not None:
            from_queue['from']['steps'].extend(remaining_steps)

        spec.append(from_queue)
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
    if 'brokers' not in config:
        raise TypeError('Kind kafka-sink requires a valid kafka broker.')
    topic = config['topic']
    kafka_brokers = config['brokers']
    to = f'kafka:{topic}?brokers={kafka_brokers}'
    if 'SASL_password' in config:
        to = _kafka_SASL_uri(topic, kafka_brokers, config['SASL_password'])

    return {
        'steps': [{
            'to': to,
        }]
    }


def telegram_sink(config):
    if 'authorization_token' not in config:
        raise TypeError('Authorization token required for telegram sink.')
    authorization_token = config['authorization_token']
    chat_id = ""
    if 'chat_id' in config:
        chat_id = config['chat_id']

    # The telegram sink yaml below allows to override the default chat ID where
    # the messages are sent.
    return {
        'steps': [{
            'convert-body-to': {
                'type': "java.lang.String"
            }
        }, {
            'to': {
                'uri': 'telegram:bots',
                'parameters': {
                    'authorizationToken': authorization_token,
                    'chatId': chat_id
                }
            }
        }, {
            'marshal': {
                'json': {}
            }
        }]
    }


def test_sink(config):
    return {'steps': [{'log': {'message': "\"${body}\""}}]}


def generic_sink(config):
    if 'spec' in config:
        if isinstance(config['spec'], str):
            return _process_generic_spec_str(config, sink=True)
        # If the sink spec is given as non-string we assume it is a valid
        # dictionary of the form:
        # {'uri':<uri_value>, 'steps':[<more yaml or empty>]}
        return config['spec']
    elif 'uri' in config:
        return {'steps': [{'to': config['uri']}]}
    else:
        raise TypeError('Kind generic-sink requires a spec or uri field.')


sinks = {
    'slack-sink': slack_sink,
    'kafka-sink': kafka_sink,
    'telegram-sink': telegram_sink,
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


def _parse_endpoint(endpoint):
    # Check URI scheme is valid:
    if endpoint.startswith("https://"):
        trimmed_endpoint = endpoint[len("https://"):]
        split_endpoint = trimmed_endpoint.split(".")

        if split_endpoint[0] != "s3":
            raise TypeError(f"Endpoint {endpoint} is not an s3 endpoint.")

        return split_endpoint

    raise TypeError(
        f"Unexpected or missing URI scheme in endpoint: {endpoint}")
