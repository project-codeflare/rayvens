# Sources and Sinks

## Introduction

Rayvens offers facilities to easily incorporate the set of Apache Camel sources and sinks into an application code.

Sources and sinks are attached to `Stream` objects:

```
stream = rayvens.Stream('name')
```

The addition of a new source or sink to a stream requires a configuration to be passed into the appropriate API function. A configuration is a dictionary containing the source or sink `kind` along with several of its options.

The general usage is to first create the configuration:
```
sink_configuration = dict(kind='slack-sink',
                          channel='channel_name',
                          webhookUrl='valid_webhook_url')
```

followed by the creation of the sink based on the configuration:

```
stream.add_sink(sink_configuration)
```

## How sources and sinks work

Sources publish events to the stream they are attached to.

Sinks are subscribed to the stream they are attached to.

Events are propagated from the sources via the stream to all the subscribers attached to the stream.

If any operator is attached to the stream, the operator will process the events in the order in which they are pushed onto the stream and then forwards them to all the sinks once the processing ends.

Locally, sources and sinks run as separate processes. This includes the case in which the source/sink is run inside a container in the cloud. When running using the operator mode, the source/sink will be launched as a service.

## Rayvens support

Rayvens supports several sources and sinks out of the box given below by their `kind` field value.

Sources:
- `http-source`
- `kafka-source`
- `telegram-source`
- `binance-source`
- `cloud-object-store-source`

Sinks:
- `slack-sink`
- `kafka-sink`
- `telegram-sink`
- `cloud-object-store-sink`

In addition to the sources and sinks above, Rayvens also allows the user to specify any other source or sink supported by Apache Camel by using the following sources/sink kinds:
- `generic-source`
- `generic-periodic-source`
- `generic-sink`

## Sources

### `kind="http-source"`

An HTTP source is a periodic source meaning that a request will be sent to the source URL every `period` milliseconds.

The source supports the following fields:
- `url` the URL being polled every `period` milliseconds
- `period` (optional, default 1000 ms) request frequency in milliseconds

```
source_config = dict(kind='http-source',
                     url=<url_value>,
                     period=3000)
```

Example of a URL value: `http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo`

### `kind="kafka-source"`

The Kafka source allows the application to receive the events published on a specific Kafka topic. It supports the following fields:
- `topic` the Kafka topic where all the events will be coming from
- `brokers` list of Kafka brokers of the following type: host1:port1,host2:port2,...
- `SASL_password` (optional) if interacting with a cloud-based Kafka service, this is the password used to access the service

### `kind="telegram-source"`

The Telegram source receives all the incoming messages from a Telegram Bot. It supports the following fields:
- `authorization_token` the authorization token used to communicate with the Telegram Bot.

### `kind="binance-source"`

Uses the Binance API to retrieve cryptocurrency prices. It supports the following fields:
- `coin` the official cryptocurrency symbol, for example for Bitcoin the symbol is BTC
- `period` (optional, default 3000 milliseconds) price request frequency in milliseconds

Example:
```
source_config = dict(kind='binance-source', coin='BTC')
```

This source supports multiple input routes based on the number of coins being interrogated:
```
source_config = dict(kind='binance-source', coin=['BTC', 'ETH'])
```
An individual event will be received with the price of each of coin in the list of coins.

### `kind="cloud-object-store-source"`

This source manages the receiving of objects from AWS S3 or IBM Cloud Object Storage. It supports the following fields:
- `bucket_name` the name of the bucket
- `access_key_id` found in the configuration of the Cloud Object Storage service;
- `secret_access_key` found in the configuration of the Cloud Object Storage service;
- `endpoint` the name of the public endpoint from the bucket configuration qualified by the URI scheme (for example, `https://`);
- `region` (optional) the region of the bucket, if left empty the region will be automatically parsed by Rayvens from the endpoint;
- `move_after_read` (optional) enables moving of any read file from bucket specified by `bucket_name` to new bucket that is the value of this field. If using the Cloud Object Storage, the new bucket has to be created ahead of time. The new bucket name is provided as the value of this field;

This source will fetch and delete the files in the bucket unless the `move_after_read` option is enabled in which case the read files are moved to the bucket specified by the `move_after_read` field value.

Example of the simplest configuration where the source consumes any files written to the bucket specified by the `bucket_name`:
```
source_config = dict(kind='cloud-object-storage-source',
                     bucket_name="input_bucket_name",
                     access_key_id=access_key_id,
                     secret_access_key=secret_access_key,
                     endpoint=endpoint)
```

Example of configuration with move after read enabled:
```
source_config = dict(kind='cloud-object-storage-source',
                     bucket_name="input_bucket_name",
                     access_key_id=<access_key_id>,
                     secret_access_key=<secret_access_key>,
                     endpoint=<endpoint>,
                     move_after_read="new-bucket-name")
```

### `kind="file-source"`

This source reads a file from the file system when the file becomes available. The event is triggered automatically whenever the file becomes available. The file content is read to memory and returned by the source to be processed further by the application. This source has the following options:
- `path` the path to the file being monitored;
- `keep_files` (optional) by default the files are deleted i.e. the value is `False`;

Example configuration for this source:
```
source_config = dict(kind='file-source',
                     path='test_files/test2.txt',
                     keep_files=True)
```

### `kind="file-watch-source"`

This source monitors a given directory for file-related events: modifications, deletion and creation. The source has the following configuration fields:
- `path` the path to the directory being monitored;
- `events` the list of events being monitored: `DELETE`, `CREATE` and `MODIFY`. By default all three events are enabled. The user can specify a subset of events only by setting the value of this field to a comma separated list example: `events=DELETE,CREATE`

Example of configuration for this source:
```
source_config = dict(kind='file-watch-source',
                     path='test_files',
                     events='DELETE,CREATE')
```

The event format for this source is:
```
<event_type>:file=<filename>
```

For example, when the file `test.txt` is deleted from the watched folder the event returned is:
```
DELETE:file=/absolute/path/to/test.txt
```


## Sinks

### `kind="slack-sink"`

Outputs a message to a Slack channel provided by the user. It supports the following fields:
- `channel` the output channel name
- `webhookUrl` the webhook URL belonging to the channel to which the message is being sent

### `kind="kafka-sink"`

The Kafka sink allows the application to publish events to a specific Kafka topic. It supports the following fields:
- `topic` the Kafka topic to which events will be sent
- `brokers` list of Kafka brokers of the following type: host1:port1,host2:port2,...
- `SASL_password` (optional) if interacting with a cloud-based Kafka service, this is the password used to access the service

### `kind="telegram-sink"`

The Telegram sink sends messages to a Telegram Bot. It supports the following fields:
- `authorization_token` the authorization token used to communicate with the Telegram Bot.
- `chat_id` (optional) if present it enables the Telegram bot to send the message to another Telegram chat.

### `kind="cloud-object-store-sink"`

This sink manages the uploading of objects to AWS S3 or IBM Cloud Object Storage. It supports the following fields:
- `bucket_name` the name of the bucket;
- `access_key_id` found in the configuration of the Cloud Object Storage service;
- `secret_access_key` found in the configuration of the Cloud Object Storage service;
- `endpoint` the name of the public endpoint from the bucket configuration qualified by the URI scheme (for example, `https://`);
- `region` (optional) the region of the bucket, if left empty the region will be automatically parsed by Rayvens from the endpoint;
- `upload_type` (optional) the special type of the upload:

  Possible values:
    - `upload_type="multi-part"` the input must be a file which will be split into multiple parts;

  Related options:
    - `part_size` (optional, only used when `upload_type` is set to `multi-part`) the size in bytes of the parts;

- `file_name` (optional when `upload_type` is `multi-part`) the name of the file under which the data will be stored in the Cloud Object Store. If specified in conjunction with `upload_type` being `multi-part` the name of the uploaded file will be overwritten;
- `from_file` (optional) uploads a file to Cloud Object Storage. The upload event is triggered when the file is available. The file is deleted after the upload unless the `keep_file` option is specified. When this option is enabled, the `upload_type` is by default `multi-part` and the file will be uploaded in multiple parts of size `part_size`;

  Related options:
  - `keep_file` (optional) this option signals that the file specified by `from_file` or the files dumped inside the `from_directory` should not be deleted after upload;

- `from_directory` (optional) uploads the files dropped into a file system directory to Cloud Object Storage. The upload event is triggered whenever a file is dropped inside the directory. The file is deleted after the upload. When this option is enabled, the `upload_type` is by default `multi-part` and the file will be uploaded in multiple parts of size `part_size`;

  Related options:
  - `keep_file` (optional) this option signals that the files dumped inside the `from_directory` should not be deleted after upload;

Without using any of the optional fields, this sink will upload application data to the Cloud Object Storage and put it in a file with name specified by the user. The data is the file contents in this case. See example `cos_sink.py`.

In addition to the default mode described above this sink type also supports the uploading of files in multiple parts. To enable this mode the upload type field named `upload_type` must be specified as `multi-part`. The configuration also accepts an optional argument `part_size` that specifies the size of the parts. The size needs to be specified in bytes and its default value is 10 MB (i.e. 26214400 bytes).

For example, to specify a multi-part upload using 2MB chunks:
```
sink_config = dict(kind='cloud-object-storage-sink',
                   bucket_name=<cos_bucket>,
                   access_key_id=<cos_access_key_id>,
                   secret_access_key=<cos_secret_access_key>,
                   endpoint=<cos_endpoint>,
                   upload_type="multi-part",
                   part_size=2 * 1024 * 1024)
```

The file to be uploaded can be specified by the user at runtime and can be passed to the Rayvens stream containing a multi-part Cloud Object Storage sink use in the following way:
```
from pathlib import Path
stream << Path("test_files/test.txt")
```

This will ensure that the input is treated as the path to a file on the target system. Unless overwritten by the `file_name` option the name of the uploaded file will be the original file name (in this case `test.txt`).

When `from_file` or `from_directory` fields are used, the input will be a file system file which is uploaded in multi-part mode. Since the multi-part mode is the only one currently supported it will be selected by default. To adjust the part size consider using the `part_size` option.

## Generic sources

To supports the rest of Apache Camel sources, Rayvens supports two generic source types.
1. Non-periodic generic source with type `kind="generic-source"`
2. Periodic generic source with type `kind="generic-periodic-source"`

Each generic source type requires a field called `spec` or a `uri` field. If both are specified the `spec` field will be used and the `uri` field will be ignored.

The `spec` field contains the Yaml specification of the source. The expected input type for `spec` is string.

The `uri` field expects the string representing just the endpoint specification.

Depending on the source, the specification can be minimal consisting just of the URI specifying the source configuration. For example, creating a kafka source using a topic with name `"newTopic"` and a local broker `localhost:9092` is as simple as:
```
source_config = dict(kind='generic-source',
                     spec="uri: kafka:newTopic?brokers=localhost:9092")
```

For an even simpler configuration we can specify the above using the `uri` field instead:
```
source_config = dict(kind='generic-source',
                     uri="kafka:newTopic?brokers=localhost:9092")
```

The `spec` string is sensitive to indentation if the configuration is more complicated, for example, if the source is a periodic source the configuration code may look like this:

```
source_config = dict(kind='generic-source',
                     spec="""
- from:
  uri: timer:tick?period=2000
  steps:
    - to: http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo
    """)
```

Every two seconds, a request will be sent to the source URL request the price of an AAPL share. The response will be forwarded back to Rayvens.

To simplify the support of periodic patterns such as the one for the generic HTTP source above, Rayvens provides a periodic generic source. Periodic generic sources use a timer to send requests to the source every `period` milliseconds in a similar manner to the code above. The request will trigger the source to produce an event which is then forwarded to Rayvens. Periodic sources have an optional `period` field.

Using the `generic-periodic-source` type instead of the `generic-source` simplifies the above code to just specifying the source URI:

```
source_config = dict(kind='generic-periodic-source',
                     spec="uri: http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo",
                     period=2000)
```

Using the `uri` syntax:
```
source_config = dict(kind='generic-periodic-source',
                     uri="http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo",
                     period=2000)
```

The catalog of Apache Camel supported components can be found here: https://camel.apache.org/components/latest/index.html

## Generic sinks

Rayvens supports generic sinks denoted by the `generic-sink` type.

Similarly to generic sources, it is sufficient to specify the sink URI inside the `spec` field as a string or use the `uri` syntax.

For example, if outputting to a Slack channel, the following generic sink can be put together provided the slack channel name and webhook URL are available in the application:

```
sink_config = dict(kind='generic-sink',
                   spec=f"to: slack:{slack_channel}?webhookUrl={slack_webhook}")
```

Using the `uri` syntax the above becomes:
```
sink_config = dict(kind='generic-sink',
                   uri=f"slack:{slack_channel}?webhookUrl={slack_webhook}")
```
