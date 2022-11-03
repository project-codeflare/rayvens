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
from pathlib import Path


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

    if password == 'modeline':
        return f'kafka:{topic}?brokers={kafka_brokers}' \
               f'&securityProtocol={security_protocol}' \
               f'&saslMechanism=PLAIN'
    return f'kafka:{topic}?brokers={kafka_brokers}' \
           f'&securityProtocol={security_protocol}' \
           f'&saslMechanism=PLAIN' \
           f'&saslJaasConfig={conf}' \
           f'&sslKeyPassword={password}'


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
    bucket_name = config['bucket_name']
    access_key_id = config['access_key_id']
    secret_access_key = 'RAW('+config['secret_access_key']+')' # add RAW() to deal with special characters in key

    split_endpoint = None

    if 'endpoint' in config:
        endpoint = config['endpoint']

        # Ensure this is a valid, supported endpoint:
        split_endpoint = _parse_endpoint(endpoint)

    # Resolve region:
    region = 'us-east'
    if 'region' in config:
        region = config['region']
    else:
        if split_endpoint:
            region = split_endpoint[1]

    # Assemble URI:
    if 'endpoint' not in config:

        uri = f'aws2-s3://{bucket_name}?accessKey={access_key_id}' \
            f'&secretKey={secret_access_key}' \
            f'&region={region}'
    else:

        uri = f'aws2-s3://{bucket_name}?accessKey={access_key_id}' \
            f'&secretKey={secret_access_key}' \
            '&overrideEndpoint=true' \
            f'&uriEndpointOverride={endpoint}' \
            f'&region={region}'

    # Move after read options:
    if 'move_after_read' in config:
        # Autocreation is not supported for COS:
        uri += '&autoCreateBucket=false'
        uri += '&moveAfterRead=true'

        new_bucket_name = config['move_after_read']
        uri += f'&destinationBucket={new_bucket_name}'

    # Only send an event that data is available do not send the
    # actual data.
    if 'meta_event_only' in config and config['meta_event_only']:
        uri += '&includeBody=false'
        uri += '&autocloseBody=true'

    return {'uri': uri, 'steps': []}

# get event content w/o any meta data
def file_source_raw(config):
    if 'path' not in config:
        raise TypeError('File source requires a path name.')
    path = Path(config['path'])
    if path.is_dir():
        uri = f'file:{str(path)}?'
    elif path.is_file():
        uri = f'file:{str(path.parent)}?filename={path.name}&'
    else:
        raise RuntimeError('The given path may either be a directory or a file. The given path {} is neither.'.format(path))

    use_amp_in_recursive = False

    # Keep files after being processed. By default, files are deleted.
    if 'keep_file' in config and config['keep_file']:
        uri += 'noop=true'
        use_amp_in_recursive = True

    # Recursive traversal of the directory, default is false.
    if 'recursive' in config and config['recursive']:
        if use_amp_in_recursive:
            uri += '&recursive=true'
        else:
            uri += 'recursive=true'

    return {'uri': uri, 'steps': []}

# get event + meta (name) in json format.
def file_source(config):
    if 'path' not in config:
        raise TypeError('File source requires a path name.')
    if all(['move_after_read' in config,'keep_file' in config and config['keep_file']]):
        raise RuntimeError('Moving files will necessarily delete them from the source. move_after_read and keep_file=True are mutually exclusive.')
        
    path = Path(config['path'])
    if path.is_dir():
        uri = f'file:{str(path)}?'
    elif path.is_file():
        uri = f'file:{str(path.parent)}?filename={path.name}&'
    else:
        raise RuntimeError('The given path may either be a directory or a file. The given path {} is neither.'.format(path))

    use_amp_in_recursive = True

    # Move after reading files from directory.
    if 'move_after_read' in config:
        move_path = Path(config['move_after_read'])
        if str(move_path) == str(path):
            raise RuntimeError(f'Path {str(move_path)} and Path {str(path)} cannot be identical.')
        if all([path.is_file(),str(move_path) == str(path.parent)]):
            raise RuntimeError(f'Path {str(move_path)} and Path {str(path.parent)} cannot be identical.')
        # by default, move_path will be created if it does not exist, hence, is_dir is not tested.
        # therefore, move reauires care when using relative paths, especially when the source is a file.
        uri += f'move={str(move_path)}'
    else:
        # Keep files after being processed. By default, files are deleted.
        if 'keep_file' in config and config['keep_file']:
            uri += 'noop=true'
        else:
            use_amp_in_recursive = False

    # Recursive traversal of the directory, default is false.
    if 'recursive' in config and config['recursive']:
        if use_amp_in_recursive:
            uri += '&recursive=true'
        else:
            uri += 'recursive=true'

    return {'uri': uri, 'steps': []}


def file_watch_source(config):
    if 'path' not in config:
        raise TypeError('File watch source requires a directory path name.')
    path = Path(config['path'])
    if not path.is_dir():
        raise RuntimeError(f'Path {str(path)} is not a directory.')

    uri = f'file-watch:{str(path)}'

    # Set up the events to be monitored. Use the events set by the user
    # otherwise enable all valid events.
    valid_events = ["DELETE", "CREATE", "MODIFY"]
    if 'events' in config:
        events = config['events']
        event_types = events.split(",")
        for event in event_types:
            if event not in valid_events:
                raise RuntimeError(f'Event type {event} is not supported,'
                                   ' must be one of: DELETE, CREATE, MODIFY')
        uri += f'?events={events}'
    else:
        uri += f'?events={",".join(valid_events)}'

    # Recursive traversal of the directory, default is false.
    if 'recursive' in config and config['recursive']:
        uri += '&recursive=true'

    uri += "&autoCreate=false"

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
    'file-source-raw': file_source_raw,
    'file-source': file_source,
    'file-watch-source': file_watch_source,
    'generic-source': generic_source,
    'generic-periodic-source': generic_periodic_source
}


def _finalize_route(spec, endpoint, inverted, add_to_queue):
    if inverted:
        spec['steps'].append({'bean': add_to_queue})
    else:
        spec['steps'].append({'to': endpoint})
    spec = [{'from': spec}]
    return spec


# Construct a camel source specification from a rayvens source config
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

    # Manage Queue access methods.
    take_from_queue = 'takeFromQueue'
    add_to_queue = 'addToQueue'
    if config['kind'] == 'file-source-raw':
        take_from_queue = 'takeFromFileQueue'
        add_to_queue = 'addToFileQueue'
    if config['kind'] == 'file-source':
        take_from_queue = 'takeFromFileQueueName'
        add_to_queue = 'addToFileQueueName'
    elif config['kind'] == 'file-watch-source':
        take_from_queue = 'takeFromFileWatchQueue'
        add_to_queue = 'addToFileWatchQueue'
    elif config['kind'] == 'cloud-object-storage-source' and \
            'meta_event_only' in config and config['meta_event_only']:
        take_from_queue = 'takeFromMetaEventQueue'
        add_to_queue = 'addToMetaEventQueue'
    elif config['kind'] == 'cloud-object-storage-source':
        take_from_queue = 'takeFromFileJsonQueue'
        add_to_queue = 'addToFileJsonQueue'

    # Multi-source integration with several routes:
    if isinstance(spec, list):
        # Generic sources do now allow multiple routes:
        if remaining_steps is not None:
            raise TypeError(
                'Generic source with multiple routes not supported')

        spec_list = []
        for spec_entry in spec:
            spec_list.extend(
                _finalize_route(spec_entry, endpoint, inverted, add_to_queue))
        if inverted:

            spec_list.append({
                'from': {
                    'uri': endpoint,
                    'steps': [{
                        'bean': take_from_queue
                    }]
                }
            })
        # print(yaml.dump(spec_list))
        return spec_list

    # Regular integration with only one route:
    spec = _finalize_route(spec, endpoint, inverted, add_to_queue)
    if inverted:
        # Route fetching from queue:
        from_queue = {
            'from': {
                'uri': endpoint,
                'steps': [{
                    'bean': take_from_queue
                }]
            }
        }

        # Attach remaining steps after fetching from the queue.
        if remaining_steps is not None:
            from_queue['from']['steps'].extend(remaining_steps)

        spec.append(from_queue)
    # print(yaml.dump(spec))
    return spec


def slack_sink(config):
    if 'channel' not in config:
        raise TypeError('Kind slack-sink requires a channel.')
    channel = config['channel']

    option_values = []
    if 'webhook_url' in config:
        webhook_url = config['webhook_url']
        option_values.append(f"webhookUrl={webhook_url}")

    options = ""
    if len(option_values) > 0:
        options = "?" + "&".join(option_values)

    final_spec = {
        'steps': [{
            'to': f'slack:{channel}{options}',
        }]
    }

    return [(final_spec, None)]


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

    final_spec = {
        'steps': [{
            'to': to,
        }]
    }
    return [(final_spec, None)]


def telegram_sink(config):
    if 'authorization_token' not in config:
        raise TypeError('Authorization token required for telegram sink.')
    authorization_token = config['authorization_token']
    chat_id = ""
    if 'chat_id' in config:
        chat_id = config['chat_id']

    # The telegram sink yaml below allows to override the default chat ID where
    # the messages are sent.
    final_spec = {
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
    return [(final_spec, None)]


def cos_sink(config):
    if 'bucket_name' not in config:
        raise TypeError('Cloud object storage sink requires a bucket name.')
    if 'access_key_id' not in config:
        raise TypeError('Cloud object storage sink requires an access key id.')
    if 'secret_access_key' not in config:
        raise TypeError(
            'Cloud object storage sink requires an secret access key.')
    bucket_name = config['bucket_name']
    access_key_id = config['access_key_id']
    secret_access_key = 'RAW('+config['secret_access_key']+')' # add RAW() to deal with special characters in key

    split_endpoint = None
    if 'endpoint' in config:
        endpoint = config['endpoint']
        # Ensure this is a valid, supported endpoint:
        split_endpoint = _parse_endpoint(endpoint)


    file_name = "default.txt"
    if 'file_name' in config:
        file_name = config['file_name']

    # Resolve region:
    region = 'us-east'
    if 'region' in config:
        region = config['region']
    else:
        if split_endpoint:
            region = split_endpoint[1]

    # If we are uploading a file either directly or by monitoring a directory,
    # multi-part must be enabled:
    uploads_file = 'from_file' in config or 'from_directory' in config
    if uploads_file:
        config['upload_type'] = "multi-part"

    # Assemble URI:
    if 'endpoint' not in config:
        uri = f'aws2-s3://{bucket_name}?accessKey={access_key_id}' \
            f'&secretKey={secret_access_key}' \
            f'&region={region}'
    else:
        uri = f'aws2-s3://{bucket_name}?accessKey={access_key_id}' \
            f'&secretKey={secret_access_key}' \
            '&overrideEndpoint=true' \
            f'&uriEndpointOverride={endpoint}' \
            f'&region={region}'

    # Final result is a list of spec and uri pairs: [(spec, uri)]
    spec_list = []

    # Streaming is only supported in latest Camel. Camel-K currently
    # supports Camel 3.9.0 only. Camel 3.10 or newer is required for
    # this feature.
    if 'upload_type' in config:
        if config['upload_type'] == "stream":
            uri += '&streamingUploadMode=true'
            uri += '&namingStrategy=progressive'
            uri += '&restartingPolicy=lastPart'
            # 1 MB sized batches are default in streaming mode.
            batch_size = 1000000  # bytes
            if 'batch_size' in config:
                batch_size = config['batch_size']
            uri += f'&batchSize={batch_size}'

            # 10 messages per batch is default in upload mode.
            messages_per_batch = 10
            if 'messages_per_batch' in config:
                messages_per_batch = config['messages_per_batch']
            uri += f'&batchMessageNumber={messages_per_batch}'
            raise TypeError("Streaming uploads not yet supported.")
        elif config['upload_type'] == "multi-part":
            uri += '&multiPartUpload=true'
            # 25 MB size per part is the default in streaming mode.
            part_size = 26214400  # bytes
            if 'part_size' in config:
                part_size = config['part_size']
            uri += f'&partSize={part_size}'

            # Initialize the part of the spec that has its source in Rayvens,
            # i.e. the part which takes as input file names from the user.
            spec = {'steps': []}
            spec['steps'].append({'bean': 'processPath'})
            # Overwrite existing file name if user provided a new name.
            if file_name is not None:
                spec['steps'].append({
                    'set-header': {
                        'name': 'CamelAwsS3Key',
                        'simple': file_name
                    }
                })
            spec['steps'].append({'to': uri})
            spec_list.append((spec, None))

            # If the from_file option is active we need to create a route
            # from the local file to the cloud object storage. For this route
            # we do not allow the overwriting of the original file name since
            # that may cause a clash with the file uploaded on the Rayvens-to-
            # COS route above for which name overwriting is supported.
            # When from_directory option is active all the files dumped into
            # a file system directory will be uploaded to Cloud Object Storage.
            # `from_file` and `from_directory` cannot be active at the same
            # time.
            if 'from_file' in config:
                # Process file path and create from_uri:
                from_file_path = Path(config['from_file'])
                uploaded_file_name = from_file_path.name
                file_dir = str(from_file_path.parent)
                from_uri = f'file:{file_dir}?filename={uploaded_file_name}'
                # Delete file after it is uploaded to avoid the files being
                # copied to a temporary folder after being uploaded.
                if 'keep_file' in config and config['keep_file']:
                    from_uri += '&delete=false'
                else:
                    from_uri += '&delete=true'

                # Create new file route for final spec:
                file_spec = {'steps': []}
                file_spec['steps'].append({'bean': 'processFile'})
                file_spec['steps'].append({'to': uri})
                spec_list.append((file_spec, from_uri))
            elif 'from_directory' in config:
                # Process file path and create from_uri:
                from_directory_path = config['from_directory']
                from_uri = f'file:{from_directory_path}'
                # Delete file after it is uploaded to avoid the files being
                # copied to a temporary folder after being uploaded.
                if 'keep_file' in config and config['keep_file']:
                    from_uri += '?delete=false'
                else:
                    from_uri += '?delete=true'

                # Create new file route for final spec:
                file_spec = {'steps': []}
                file_spec['steps'].append({'bean': 'processFile'})
                file_spec['steps'].append({'to': uri})
                spec_list.append((file_spec, from_uri))
            return spec_list
        else:
            raise TypeError(
                "Unrecognized upload type. Use one of: stream, multi-part.")

    # This is the default behavior when user application data is
    # written into a COS file directly.
    if 'file_name' in config:
        regular_spec = {
            'steps': [{
                'set-header': {
                    'name': 'CamelAwsS3Key',
                    'simple': f"{file_name}"
                }
            }, {
                'to': uri
            }]
        }
    else:
        regular_spec = {'steps': [{'to': uri}]}
    spec_list.append((regular_spec, None))
    return spec_list


def file_sink(config):
    if 'path' not in config:
        raise TypeError('File source requires a path name.')
    path = Path(config['path'])
    if path.is_dir():
        uri = f'file:{str(path)}?'
    elif path.is_file():
        uri = f'file:{str(path.parent)}?filename={path.name}' # TODO: test this option
    else:
        raise RuntimeError('Path {} is neither a directory nor a file.'.format(config['path']))

    final_spec = {
        'steps': [{
            'to': uri,
        }]
    }

    return [(final_spec, None)]


def test_sink(config):
    return [({'steps': [{'log': {'message': "\"${body}\""}}]}, None)]


def generic_sink(config):
    if 'spec' in config:
        if isinstance(config['spec'], str):
            return [(_process_generic_spec_str(config, sink=True), None)]
        # If the sink spec is given as non-string we assume it is a valid
        # dictionary of the form:
        # {'uri':<uri_value>, 'steps':[<more yaml or empty>]}
        return [(config['spec'], None)]
    elif 'uri' in config:
        return [({'steps': [{'to': config['uri']}]}, None)]
    else:
        raise TypeError('Kind generic-sink requires a spec or uri field.')


sinks = {
    'slack-sink': slack_sink,
    'kafka-sink': kafka_sink,
    'telegram-sink': telegram_sink,
    'cloud-object-storage-sink': cos_sink,
    'file-sink': file_sink,
    'generic-sink': generic_sink,
    'test-sink': test_sink
}


# Construct a camel sink specification from a rayvens sink config.
def construct_sink(config, endpoint):
    if 'kind' not in config:
        raise TypeError('A Camel sink needs a kind.')
    kind = config['kind']
    sink_handler = sinks.get(kind)
    if sink_handler is None:
        raise TypeError(f'Unsupported Camel sink: {kind}.')

    spec_list = sink_handler(config)

    # Add the from uri construct to each route and finalize spec.
    final_spec_list = []
    for spec_uri_pair in spec_list:
        spec = spec_uri_pair[0]
        from_uri = spec_uri_pair[1]
        if from_uri is None:
            spec['uri'] = endpoint
        else:
            spec['uri'] = from_uri
        final_spec_list.append({'from': spec})
    return final_spec_list


def no_restriction(config):
    return dict(restricted_message_types=[])


def cos_sink_restriction(config):
    # The input type for this sink is a file denoted by the type Path.
    if 'upload_type' in config and config['upload_type'] == 'multi-part' and \
       'from_directory' not in config:
        return dict(restricted_message_types=[Path])
    return no_restriction(config)


sink_input_restriction = {
    'slack-sink': no_restriction,
    'kafka-sink': no_restriction,
    'telegram-sink': no_restriction,
    'cloud-object-storage-sink': cos_sink_restriction,
    'file-sink': no_restriction,
    'generic-sink': no_restriction,
    'test-sink': no_restriction
}


# Return a dict of valid message types
def input_restriction(config):
    if 'kind' not in config:
        raise TypeError('A Camel sink needs a kind.')
    handler = sink_input_restriction.get(config['kind'])
    return handler(config)


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
