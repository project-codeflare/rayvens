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


def http_source():
    return dict(required=['url'], optional=['period'])


def kafka_source():
    return dict(required=['topic', 'brokers'],
                optional=['SASL_password', 'JAAS_config'])


def telegram_source():
    return dict(required=['authorization_token'], optional=[])


def binance_source():
    return dict(required=['coin'], optional=['period'])


def cos_source():
    return dict(required=[
        'bucket_name', 'access_key_id', 'secret_access_key', 'endpoint'
    ],
                optional=['region', 'move_after_read', 'meta_event_only'])


def file_source():
    return dict(required=['path'], optional=['keep_files', 'recursive'])


def file_watch_source():
    return dict(required=['path'], optional=['events', 'recursive'])


def generic_source():
    return dict(required=[], optional=[], pair=[('uri', 'spec')])


def generic_periodic_source():
    return dict(required=[], optional=['period'], pair=[('uri', 'spec')])


source_requirements = {
    'http-source': http_source,
    'kafka-source': kafka_source,
    'telegram-source': telegram_source,
    'binance-source': binance_source,
    'cloud-object-storage-source': cos_source,
    'file-source': file_source,
    'file-watch-source': file_watch_source,
    'generic-source': generic_source,
    'generic-periodic-source': generic_periodic_source
}


def slack_sink():
    return dict(required=['channel', 'webhook_url'], optional=[])


def kafka_sink():
    return dict(required=['topic', 'brokers'], optional=['SASL_password'])


def telegram_sink():
    return dict(required=['authorization_token'], optional=['chat_id'])


def cos_sink():
    return dict(required=[
        'bucket_name', 'access_key_id', 'secret_access_key', 'endpoint'
    ],
                optional=[
                    'region', 'file_name', 'from_file', 'from_directory',
                    'upload_type', 'batch_size', 'messages_per_batch',
                    'part_size', 'keep_file'
                ])


def generic_sink():
    return dict(required=[], optional=[], pair=[('uri', 'spec')])


sink_requirements = {
    'slack-sink': slack_sink,
    'kafka-sink': kafka_sink,
    'telegram-sink': telegram_sink,
    'cloud-object-storage-sink': cos_sink,
    'generic-sink': generic_sink
}


def integration_requirements(kind):
    handler = source_requirements.get(kind)
    if handler is None:
        handler = sink_requirements.get(kind)
        if handler is None:
            raise TypeError(f'Unsupported Camel source or sink: {kind}.')
    return handler()


def print_predefined_integrations():
    print(" Predefined sources:")
    for integration_type in source_requirements:
        print(f"     {integration_type}")
    print(" Predefined sinks:")
    for integration_type in sink_requirements:
        print(f"     {integration_type}")


def print_requirements_summary(kind):
    requirements = integration_requirements(kind)

    print(f" Integration: {kind}")
    if len(requirements['required']) > 0:
        print("    Required properties:")
        for req_property in requirements['required']:
            print(f"        {req_property}")
    if len(requirements['optional']) > 0:
        print("    Optional properties:")
        for opt_property in requirements['optional']:
            print(f"        {opt_property}")
    if 'pair' in requirements and len(requirements['pair']) > 0:
        print("    At least one of the properties is required:")
        for pair_property in requirements['pair']:
            print(f"        {pair_property}")


def get_all_properties(kind):
    all_properties = []
    requirements = integration_requirements(kind)
    all_properties.extend(requirements['required'])
    all_properties.extend(requirements['optional'])
    if 'pair' in requirements:
        for pair in requirements['pair']:
            all_properties.append(pair.first)
            all_properties.append(pair.second)
    return all_properties


source_modeline_name = {
    'http-source': "http",
    'kafka-source': "kafka",
    'telegram-source': "telegram",
    'binance-source': "xchange.binance",
    'cloud-object-storage-source': "aws2-s3",
    'file-source': "file",
    'file-watch-source': "file-watch"
}

sink_modeline_name = {
    'slack-sink': "slack",
    'kafka-sink': "kafka",
    'telegram-sink': "telegram",
    'cloud-object-storage-sink': "aws2-s3"
}


def get_modeline_component_name(kind):
    component_name = None
    if kind in source_modeline_name:
        component_name = source_modeline_name.get(kind)
    if kind in sink_modeline_name:
        component_name = sink_modeline_name.get(kind)
    if component_name is None:
        raise TypeError(f'Modeline unsupported for source or sink: {kind}.')
    return "camel.component." + component_name


modeline_property_name_exceptions = {
    'SASL_password': 'sslKeyPassword',
    'JAAS_config': 'saslJaasConfig',
    'authorization_token': 'authorizationToken',
    'access_key_id': 'accessKey',
    'secret_access_key': 'secretKey',
    'endpoint': 'uriEndpointOverride',
    'move_after_read': 'destinationBucket',
    'webhook_url': 'webhookUrl',
    'batch_size': 'batchSize',
    'messages_per_batch': 'batchMessageNumber',
    'part_size': 'partSize',
}


def get_modeline_property_name(property_name):
    if property_name in modeline_property_name_exceptions:
        return modeline_property_name_exceptions.get(property_name)

    if property_name in cannot_be_modeline_property:
        raise TypeError(
            f'Cannot pass property {property_name} via environment variable.')
    return property_name


cannot_be_modeline_property = [
    'url', 'topic', 'channel', 'coin', 'period', 'meta_event_only', 'path',
    'keep_files', 'events', 'chat_id', 'bucket_name', 'file_name', 'from_file',
    'from_directory', 'upload_type'
]


def can_be_modeline_property(property_name):
    return property_name not in cannot_be_modeline_property


def get_modeline_properties(kind, envvars):
    # We assume at this point that:
    # 1. All property env var pairs are syntactically correct
    # 2. The property env var pairs do not contain properties that
    #    cannot be modelined.
    component_name = get_modeline_component_name(kind)

    modeline_properties = {}
    for property_env_pair in envvars:
        components = property_env_pair.split("=")
        property_name = components[0]
        env_var_name = "{{env:" + components[1] + "}}"

        print("property_name=", property_name)

        # Modeline property format:
        # # camel-k: property=<property_name>={{env:<env_var>}}
        modeline_property = get_modeline_property_name(property_name)
        print("modeline_property=", modeline_property)
        modeline_property = ".".join([component_name, modeline_property])
        modeline_property = "=".join(
            ["property", modeline_property, env_var_name])
        modeline_properties[property_name] = "# camel-k: " + modeline_property
    return modeline_properties


def fill_config(kind, property_value_list, show_missing=True):
    requirements = integration_requirements(kind)

    config = dict(kind=kind)

    # Assume list is of the form `property=value`
    for property_value in property_value_list:
        if "=" not in property_value:
            raise RuntimeError(
                f"Invalid property-value pair: {property_value}")

        components = property_value.split("=")
        config[components[0]] = components[1]

    # Check all requirements have been fulfilled.
    missing_requirements = []
    if len(requirements['required']) > 0:
        for req_property in requirements['required']:
            if req_property not in config:
                missing_requirements.append(req_property)

    if show_missing and len(missing_requirements) > 0:
        print(f" Missing required properties for integration type {kind}:")
        for missing_req in missing_requirements:
            print(f"    {missing_req}")

    return config, missing_requirements
