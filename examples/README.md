<!--
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
-->

# Rayvens examples

This folder contains several examples of Rayvens usage.

Before running the following examples, follow the installation instructions outlined in the main README file.


## Hello World

Event streams, i.e. instances of the `Stream` class, represent the core element of the Rayvens API:

```
import rayvens
stream = rayvens.Stream('example')
```

In the `stream.py` example we send a `hello world` string message to an event stream.

To launch example on the local machine:

```
python stream.py
```

To launch the example in a container using the Rayvens custom image inside a cluster:
```
ray submit ../scripts/cluster.yaml stream.py
```

## Subscriber types examples

Rayvens event streams can be subscribed to and can have events published to them.

An event published to a Rayvens stream will be delivered to all its subscribers.

Rayvens allows for several types of stream subscribers: Python functions, Ray tasks, Ray actor methods, or even other Rayvens streams.

### Subscribe functions to Rayvens streams

Functions can be subscribed to streams:

```
# define a Python function as an event handler
def function(event):
    print('function received', event)

# subscribe Python function to Rayvens event stream
stream >> function
```

Run example `function.py` the example on the local machine:
```
python function.py
```

To launch the example in a container using the Rayvens custom image inside a cluster:
```
ray submit ../scripts/cluster.yaml function.py
```

### Subscribe Ray tasks to Rayvens streams

Ray tasks can be subscribed to Rayvens streams:
```
# define a Ray task as an event handler
@ray.remote
def task(event):
    print('task received', event)

# subscribe Ray task to Rayvens event stream
stream >> task
```

Run example `task.py` locally using:
```
python task.py
```

To launch the example in a container using the Rayvens custom image inside a cluster:
```
ray submit ../scripts/cluster.yaml task.py
```

### Subscribe Ray actor methods to Rayvens streams

Ray actor methods can be subscribed to Rayvens streams:
```
# Ray actor
@ray.remote
class Accumulator:
    def __init__(self, name):
        self.value = 0

    def actor_method(self, delta):
        self.value += delta
        print('Value =', self.value)

# Instantiate actor:
acc = Accumulator.remote('actor_name')

# Subscribe Ray actor method to Rayvens event stream:
stream >> acc.actor_method
```

If no actor method is explicitly specified a method called `append` is assumed.

Run example `actor.py` on the local machine:
```
python actor.py
```

To launch the example in a container using the Rayvens custom image inside a cluster:
```
ray submit ../scripts/cluster.yaml actor.py
```

### Subscribing Rayvens streams

Rayvens supports subscription between Rayvens streams.

The `slack.py` example showcases this using several streams:
- a stream that has the source
- a stream that has the operator (event processor)
- a stream that has the sink

For the full code please see the example but in short, looking at just the creation of the streams:
```
# Streams
source = rayvens.Stream('http', source_config=source_config)
operator = rayvens.Stream('comparator', operator=comparator)
sink = rayvens.Stream('slack', sink_config=sink_config)

# Subscription between streams:
source >> operator >> sink
```

This feature of Rayvens will be used in several of the following examples.

## Specialized sources and sinks

In addition to the support for generic sources and sinks, Rayvens leverages Camel-K to support more specialized types of sources and sinks.

### HTTP source

In `source.py` we configure an HTTP source:

```
source_config = dict(
    kind='http-source',
    url='https://query1.finance.yahoo.com/v7/finance/quote?symbols=AAPL',
    period=3000)
source = rayvens.Stream('http', source_config=source_config)
```

The source will perform a request to the url specified in the configuration every 3000 ms. The url and the frequency can be adjusted. The result of that request will then be forwarded to the `http` event stream. The creation of the source and of the Stream happen at the same time. Any subscriber to the stream will receive the event.

To launch the example on the local machine:

```
python source.py
```

To launch the example in a container using the Rayvens custom image inside a cluster:
```
ray submit ../scripts/cluster.yaml source.py
```

### Slack sink

In `slack.py` a Slack sink is configured:

```
sink_config = dict(kind='slack-sink',
                   channel=slack_channel,
                   webhook_url=slack_webhook)
sink = rayvens.Stream('slack', sink_config=sink_config)
```

A Slack sink requires a valid webhook to be set up by the user. The webhook is then used to enable messages to be sent to the Slack channel. Any event appended to the slack event stream will be forwarded to the Slack channel named by the `slack_channel` variable.

The slack channel name and webhook URL need to be passed in as command line arguments either directly:
```
python slack.py <slack_channel> <slack_webhook>
```

or via environment variables:
```
python slack.py $SLACK_CHANNEL $SLACK_WEBHOOK
```

The commands above will run the `slack.py` example on the local machine.

To launch the example in a container using the Rayvens custom image inside a cluster:
```
ray submit ../scripts/cluster.yaml slack.py <slack_channel> <slack_webhook>
```

### Kafka sources and sinks

In `kafka_operator_mode.py` we configure a Kafka source and a Kafka sink:
```
source_config = dict(kind='kafka-source',
                     topic=topic,
                     broker=broker)
source = source_stream.add_source(source_config)

sink_config = dict(kind='kafka-sink',
                   topic=topic,
                   broker=broker)
sink = sink_stream.add_sink(sink_config)
```

The presence of a Kafka service is required. The messages will be received/published from the respective Kafka topic. In this particular example, the same topic is used to verify that the message is being propagated correctly.

Run example `kafka_operator_mode.py` on the local machine:
```
python kafka_operator_mode.py
```

To launch the example in a container using the Rayvens custom image inside a cluster:
```
ray submit ../scripts/cluster.yaml kafka_operator_mode.py local
```

## Using different modes

Rayvens allows for several run modes to be used in addition to the default local mode.

### Operator mode

The `operator` mode requires the Camel-K Kubernetes operator to be installed. In operator mode, the Camel-K operator will be used to create each source/sink process as an actual Kubernetes service.

Several of the examples may be launched in operator mode:
```
ray submit ../scripts/cluster.yaml slack_operator_mode.py <slack_channel> <slack_webhook> operator
```

Using `kubectl get all -n ray` will reveal the services and pods created. Make sure the execute this command while the example is running because any services and pods created by the example are automatically cleaned-up by Rayvens once the application exits.

For HTTP sources:
```
ray submit ../scripts/cluster.yaml source_operator_mode.py operator
```

For Kafka sources and sinks:
```
ray submit ../scripts/cluster.yaml kafka_operator_mode.py operator
```

### Mixed mode

In `mixed` mode the non-Camel-K parts of the application will be run on the local machine while the Camel-K sources and sinks will be created as Kubernetes services.

```
ray submit ../scripts/cluster.yaml slack_operator_mode.py <slack_channel> <slack_webhook> mixed
ray submit ../scripts/cluster.yaml source_operator_mode.py mixed
ray submit ../scripts/cluster.yaml kafka_operator_mode.py mixed
```
