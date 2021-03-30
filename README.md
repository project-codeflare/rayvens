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

<p align="center">
  <img src="resources/logo.png" />
</p>

[![Build
Status](https://travis.ibm.com/solsa/rayvens.svg?token=U6PyxAbhWqm58XLxT7je&branch=master)](https://travis.ibm.com/solsa/rayvens)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](http://www.apache.org/licenses/LICENSE-2.0)

Rayvens augments [Ray](https://ray.io) with events. With Rayvens, Ray
applications can produce events, subscribe to event streams, and process events.
Rayvens leverages [Apache Camel](https://camel.apache.org) to make it possible
for data scientists to access hundreds data services with little effort.

For example, we can periodically fetch the AAPL stock price from a REST API with
code:
```python
source_config = dict(
    kind='http-source',
    url='http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo',
    period=3000)
source = rayvens.Stream('http', source_config=source_config)
```

We can publish messages to Slack with code:
```python
sink_config = dict(kind='slack-sink',
                   channel=slack_channel,
                   webhookUrl=slack_webhook)
sink = rayvens.Stream('slack', sink_config=sink_config)
```

We can delivers all events from `source` to `sink` using code:
```python
source >> sink
```

We also process events on the fly using Python functions, Ray tasks, or Ray
actors for stateful processing. For instance, we can log events to the console
using code:
```python
source >> (lambda event: print('LOG:', event))
```

## Setup Rayvens

These instructions have been tested on Big Sur and Ubuntu 18.04.4.

We recommend installing Python 3.8.7 using
[pyenv](https://github.com/pyenv/pyenv).

Install Ray and Ray Serve with Kubernetes support:
```shell
pip install --upgrade pip

# for osx
pip install https://s3-us-west-2.amazonaws.com/ray-wheels/master/9053be0e639cf35a1b113ca8a4fc378d209ecb75/ray-2.0.0.dev0-cp38-cp38-macosx_10_13_x86_64.whl

# for linux
pip install https://s3-us-west-2.amazonaws.com/ray-wheels/master/9053be0e639cf35a1b113ca8a4fc378d209ecb75/ray-2.0.0.dev0-cp38-cp38-manylinux2014_x86_64.whl

# for both
pip install "ray[serve]"
pip install kubernetes
```

Clone this repository and install Rayvens:
```shell
git clone https://github.ibm.com/solsa/rayvens.git
pip install rayvens
```

Try Rayvens:
```shell
python rayvens/examples/stream.py
```
```
(pid=37214) LOG: hello
(pid=37214) LOG: world
```

## A First Example

The [stream.py](examples/stream.py) file demonstrates an elementary Rayvens
program.
```python
import ray
import rayvens

# initialize ray
ray.init()

# initialize rayvens
rayvens.init()

# create a stream
stream = rayvens.Stream('example')

# log all future events
stream >> (lambda event: print('LOG:', event))

# append two events to the stream in order
stream << 'hello' << 'world'
```

This program initialize Ray and Rayvens and creates a `rayvens.Stream` instance.
Streams and events are the core facilities offered by Rayvens. Streams bridge
event publishers and subscribers.

In this example, a subscriber is added to the stream using syntax `stream >>
subscriber`. The `>>` operator is a shorthand for the `send_to` method:
```python
stream.send_to(lambda event: print('LOG:', event))
```
All events appended to the stream _after_ the invocation of the `>>` operator
(or `send_to` method) will be delivered to the subscriber. Multiple subscribers
may be attached to the same stream. In general, subscribers can be Python
functions, Ray tasks, or Ray actors. Hence, streams can interface publishers and
subscribers running on different Ray nodes.

A couple of events are then published to the stream using the syntax `stream <<
value`. As illustrated here, events are just arbitrary values in general, but of
course publishers and subscribers can agree on specific event schemas. The `<<`
operator has left-to-right associativity making it possible to send multiple
events with one statement. The `<<` operator is a shorthand for the `append`
method:
```python
stream.append('hello').append('world')
```

Conceptually, the `append` method adds an event _at the end_ of the stream, just
like the `append` method of Python lists. But in contrast with lists, a Stream
does not persist events. It simply delivers events to subscribers as they come.
In particular, appending events to a stream without subscribers (and without an
operator, see below) is a no-op.

Run the example program with:
```shell
python rayvens/examples/stream.py
```
```
(pid=37214) LOG: hello
(pid=37214) LOG: world
```

Observe the two events are delivered in order. Events are delivered to function
and actor subscribers in order, but task subscribers offer no ordering
guarantees. See the [function.py](examples/function.py),
[task.py](examples/task.py), and [actor.py](examples/actor.py) examples for
details.

The `<<` and `>>` operator are not symmetrical. The `send_to` method (resp. `>>`
operator) invokes its argument (resp. right-hand side) for every event appended
to the stream. The `append` method and `<<` operator only append one event to
the stream.

## Stream and StreamActor

Under the hood, streams are implemented as Ray actors. Concretely, the
`rayvens.Stream` class is a stateless, serializable, wrapper around the
`rayvens.StreamActor` actor class. All rules applicable to Ray actors
(lifecycle, serialization, queuing, ordering) are applicable to streams. In
particular, the stream actor will be reclaimed when the original stream handle
goes out of scope.

The configuration of the stream actor can be tuned using `actor_options`:
```python
stream = rayvens.Stream('example', actor_options={num_cpus: 0.1})
```

For convenience, most methods of the `Stream` class including the `send_to`
method encapsulate the remote invocation of the homonymous `StreamActor` method
and block until completion using `ray.get`. The `append` method is the
exception. It returns immediately. Nevertheless, Ray actor's semantics
guarantees that sequences of `append` invocations are processed in order.

For more control, it is possible to invoke methods directly on the stream actor,
for example:
```python
stream.actor.send_to.remote(lambda event: print('LOG:', event))
```

## Setup Camel-K

To run Rayvens programs including Camel components, there are three choices:
1. **local mode**: run Ray on the host with a local installation of the Camel-K
   client, Java, and Maven,
2. **operator mode**: run Ray and Camel-K inside a Kubernetes cluster relying on
   the [Camel-K
   operator](https://camel.apache.org/camel-k/latest/architecture/operator.html)
   to run Camel components in dedicated pods,
3. **anywhere mode**: run Ray and Camel-K inside a Kubernetes cluster without
   relying on the [Camel-K
   operator](https://camel.apache.org/camel-k/latest/architecture/operator.html)
   by running the Camel components inside the Ray pods in jointly with the Ray
   processes.

Modes 2 and 3 rely on a custom Ray container image that adds to the base Ray
image the Rayvens package and the kamel CLI and its dependencies. This image is
built automatically as part of the setup described below. This setup also
includes the deployment of the Camel-K operator used in mode 2 and the necessary
RBAC rules for the operator.

In principle, mode 3 permits running Rayvens anywhere Ray can by simply
replacing the base Ray image with the Rayvens image. At this time however, we
only include deployment instructions for Kubernetes.

### Setup Camel-K on the host

To run Camel event sources and sinks locally, a [Camel-K
client](https://camel.apache.org/camel-k/latest/cli/cli.html) installation is
required. Download the Camel-K client from the [release
page](https://github.com/apache/camel-k/releases/tag/v1.3.1) and put it in your
path. Install a Java 11 JDK. Install Apache Maven 3.6.3.

Test your installation with:
```shell
kamel local run rayvens/scripts/camel-test-source.yaml
```

### Setup Ray and Camel-K in Kind

To test Rayvens on a development Kubernetes cluster we recommend using
[Kind](https://kind.sigs.k8s.io).

We assume [Docker Desktop](https://www.docker.com/products/docker-desktop) is
installed. We assume Kubernetes support in Docker Desktop is turned off. We
assume `kubectl` is installed.

Follow [instructions](https://kind.sigs.k8s.io/docs/user/quick-start) to install
the Kind client.

Setup Ray on Kind:
```shell
./rayvens/scripts/start-kind.sh
```
This script launches a persistent docker registry on the host at port 5000,
build the custom Rayvens image, creates a Kind cluster, installs Ray on this
cluster as well as the [Camel-K
operator](https://camel.apache.org/camel-k/latest/architecture/operator.html).

Try your Ray cluster on Kind with:
```shell
ray submit rayvens/scripts/cluster.yaml rayvens/examples/pubsub.py
```

### Cluster.yaml

Our example [cluster.yaml](scripts/cluster.yaml) configuration file is derived
from Ray's
[example-full.yaml](https://github.com/ray-project/ray/blob/master/python/ray/autoscaler/kubernetes/example-full.yaml)
configuration file with some notable enhancements:
- additional configuration parameters for the head and worker pods (RBAC rules
  to manage Camel integrations, downward api, custom resource tags),
- an additional service port (8000) to receive external events from Camel,
- file mounts and the installation of Rayvens of every node,
- a 2-cpu-per-pod resource requirement to make room for Ray Serve.

We plan to support the Ray operator in the near future.

### Cleanup Kind

To take down the Kind cluster (including Ray and Camel-K) run:
```shell
kind delete cluster
```

To take down the docker registry run:
```
docker stop registry
docker rm registry
```

## Event Source Example

The [source.py](examples/source.py) example demonstrates how to process external
events with Rayvens.

First, we create a stream connected to an external event source:
```python
source_config = dict(
    kind='http-source',
    url='http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo',
    period=3000)
source = client.create_stream('http', source=source_config)
```
An event source configuration is a dictionary. The `kind` key specifies the
source type. Other keys vary. An `http-source` periodically makes a REST call to
the specified `url`. The `period` is expressed in milliseconds. The events
generated by this source are the bodies of the responses encoded as strings.

In this example, we use the `http-source` to fetch the current price of the AAPL
stock.

We then implement a Ray actor to process these events:
```python
@ray.remote
class Comparator:
    def __init__(self):
        self.last_quote = None

    def append(self, event):
        payload = json.loads(event)  # parse event string to json
        quote = payload[0]['price']  # payload[0] is AAPL
        try:
            if self.last_quote:
                if quote > self.last_quote:
                    print('AAPL is up')
                elif quote < self.last_quote:
                    print('AAPL is down')
                else:
                    print('AAPL is unchanged')
        finally:
            self.last_quote = quote

comparator = Comparator.remote()
```

This actor instance compares the current price with the last price and prints a
message accordingly.

We then simply subscribe the `comparator` actor instance to the `source` stream.
```python
source >> comparator
```

By using a Ray actor to process events, we can implement stateful processing and
guarantee that events will be processed in order.

The `Comparator` class follows the convention that it accepts events by means of
a method named `append`. If for instance this method were to be named `accept`
instead, then we would have to subscribe the actor to the source using syntax
`source >> comparator.accept`.

### Running the example

Run the example locally with:
```shell
python run rayvens/examples/source.py
```

Run the example on Kind with:
```shell
ray submit rayvens/scripts/cluster.yaml rayvens/examples/source.py
```

When running locally, the Camel-K client may need to download and cache
dependencies on first run (using Maven). When running on Kubernetes, the Camel-K
operator is used to build and cache a container image for source. In both cases,
the the source may take a minute or more to start the first time. The source
should start in matter of seconds on subsequent runs.

Rayvens manages the Camel processes automatically and in most case should be
able to terminate these processes when the main program exits. In rare case,
there may be leftover `java` and `kamel` processes when running locally or
Kubernetes `integrations` objects. Please clean these manually.

## Event Sink Example

The [slack.py](examples/slack.py) builds upon the previous example by pushing
the output messages to [Slack](https://slack.com).

In addition to the same source as before, it instantiates a sink:
```python
sink_config = dict(kind='slack-sink',
                   channel=slack_channel,
                   webhookUrl=slack_webhook)
sink = client.create_stream('slack', sink=sink_config)
```
This sink sends messages to Slack. It requires two configuration parameters that
must be provided as command-line parameters to the program:
- the slack channel to publish to, e.g., `#test`, and
- a webhook url for this channel.

Please refer to the [Slack webhooks](https://api.slack.com/messaging/webhooks)
documentation for details on how to obtain these.

This example program includes a `Comparator` actor similar to the previous
example:
```python

# Actor to compare APPL quote with last quote
@ray.remote
class Comparator:
    def __init__(self):
        self.last_quote = None

    def append(self, event):
        payload = json.loads(event)  # parse event string to json
        quote = payload[0]['price']  # payload[0] is AAPL
        try:
            if self.last_quote:
                if quote > self.last_quote:
                    return 'AAPL is up'
                elif quote < self.last_quote:
                    return 'AAPL is down'
                else:
                    return 'AAPL is unchanged'
        finally:
            self.last_quote = quote


# comparator instance
comparator = Comparator.remote()
```

We can then interface the source and sink using this comparator:
```
source >> comparator >> sink
```

The `source >> comparator` expression implicitly produces a new stream of events
derived from the source stream by invoking the append method of the comparator
instance onto each source event. This stream consists of the values returned by
the append method excluding the None values. In other words, the complete line
of code is a shorthand for:
```
implicit_stream = source >> comparator
implicit_stream >> sink
```

### Running the example

We assume the `SLACK_CHANNEL` and `SLACK_WEBHOOK` environment variables contain
the necessary configuration parameters.

Run the example locally with:
```shell
python run rayvens/examples/sink.py "$SLACK_CHANNEL" "$SLACK_WEBHOOK"
```

Run the example on Kind with:
```shell
ray submit rayvens/scripts/cluster.yaml rayvens/examples/sink.py "$SLACK_CHANNEL" "$SLACK_WEBHOOK"
```

## License

Rayvens is an open-source project with an [Apache 2.0 license](LICENSE.txt).
