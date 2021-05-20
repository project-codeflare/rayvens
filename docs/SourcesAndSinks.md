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
- `access_key_id` found in the configuration of the Cloud Object Storage service.
- `secret_access_key` found in the configuration of the Cloud Object Storage service.
- `endpoint` the name of the public endpoint from the bucket configuration qualified by the URI scheme (for example, `https://`)
- `region` (optional) the region of the bucket, if left empty the region will be automatically parsed by Rayvens from the endpoint

Without any other option this source will fetch and delete the files in the bucket.

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
