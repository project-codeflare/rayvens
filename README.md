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
Status](https://travis-ci.com/project-codeflare/rayvens.svg?branch=main)](https://travis-ci.com/github/project-codeflare/rayvens)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](http://www.apache.org/licenses/LICENSE-2.0)

Rayvens augments [Ray](https://ray.io) with events. With Rayvens, Ray
applications can subscribe to event streams, process and produce events. Rayvens
leverages [Apache Camel](https://camel.apache.org) to make it possible for data
scientists to access hundreds of data services with little effort.

For example, we can periodically fetch the AAPL stock price from a REST API with
code:
```python
source_config = dict(
    kind='http-source',
    url='https://query1.finance.yahoo.com/v7/finance/quote?symbols=AAPL',
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

We can delivers all events from the `source` stream to the `sink` using code:
```python
source >> sink
```

We also process events on the fly using Python functions, Ray tasks, or Ray
actors and actor methods for stateful processing. For instance, we can log
events to the console using code:
```python
source >> (lambda event: print('LOG:', event))
```

## Setup Rayvens

Rayvens is compatible with Ray 1.3 and up.

Rayvens is intended to run anywhere Ray can. Rayvens is routinely tested on
macOS 11 (Big Sur) and Ubuntu 18 (Bionic Beaver). Rayvens is distributed both as
a Python package on [pypi.org](https://pypi.org/project/rayvens/) and as a
container image on [quay.io](https://quay.io/repository/ibm/rayvens).

To install the latest Rayvens release run:
```shell
pip install rayvens
```

We recommend cloning this repository to obtain the example programs it offers:
```shell
git clone https://github.com/project-codeflare/rayvens
```

The Rayvens package makes it possible to run Ray programs that leverage Rayvens
streams to produce and consume _internal_ events. This package does not install
Apache Camel, which is necessary to run programs that connect to _external_
event sources and sinks. We discuss the Camel setup and the Rayvens container
image [below](#camel-setup).

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

This program initialize Ray and Rayvens and creates a `Stream` instance. Streams
and events are the core facilities offered by Rayvens. Streams bridge event
publishers and subscribers.

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
value`. In contrast to subscribers that are registered with the stream, there is
no registration needed to publish event to the stream.

As illustrated here, events are just arbitrary values in general, but of course
publishers and subscribers can agree on specific event schemas. The `<<`
operator has left-to-right associativity making it possible to send multiple
events with one statement. The `<<` operator is a shorthand for the `append`
method:
```python
stream.append('hello').append('world')
```

Conceptually, the `append` method adds an event _at the end_ of the stream, just
like the `append` method of Python lists. But in contrast with lists, a stream
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

Under the hood, streams are implemented as Ray actors. Concretely, the `Stream`
class is a stateless, serializable, wrapper around the `StreamActor` Ray actor
class. All rules applicable to Ray actors (lifecycle, serialization, queuing,
ordering) are applicable to streams. In particular, the stream actor will be
reclaimed when the original stream handle goes out of scope.

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

## Camel Setup

Rayvens uses
[Camel-K](https://developers.redhat.com/blog/2020/05/12/six-reasons-to-love-camel-k).
to interact with a wide range of external source and sink types such as Slack, Cloud
Object Storage, Telegram or Binance (to name a few). Camel-K augments Apache
Camel's extensive component catalog with support for Kubernetes and serverless
platforms. Rayvens is compatible with Camel-K 1.3 and up.

To run Rayvens programs including Camel sources and sinks, there are two
choices:
- local mode: run a Camel source or sink in the same execution context as the
  stream actor it is attached to using the [Camel-K
  client](https://camel.apache.org/camel-k/latest/cli/cli.html): same container,
  same virtual or physical machine.
- operator mode: run a Camel source or sink inside a Kubernetes cluster relying
  on the [Camel-K
  operator](https://camel.apache.org/camel-k/latest/architecture/operator.html)
  to manage dedicated Camel pods.

The default mode is the local mode. The mode can be specified when initializing
Rayvens:
```python
rayvens.init(mode='operator')
```

The mode can also be specified using environment variable `RAYVENS_MODE`. 
The mode specified in the code (if any) takes precedence.

### Local Mode Prerequisites

Local mode is intended to permit running Rayvens anywhere Ray runs: on a
developer laptop, in a virtual machine, inside a Ray cluster (running on
Kubernetes or OpenShift for example), or standalone.

Local mode requires the [Camel-K
client](https://camel.apache.org/camel-k/latest/cli/cli.html), Java, and Maven
to be installed in the context in which the source or sink will be run.
When running in a cluster, Java and Maven can be added to an existing Ray
installation or image. The Rayvens image is based on a Ray image onto which we
add the necessary dependencies to enable the running of Camel-K sources and
sinks in local mode inside the container.
The all-in-one Rayvens container image distributed on
[quay.io](https://quay.io/repository/ibm/rayvens) adds Camel-K 1.4 to a base
`rayproject/ray:1.4.0-py38` image. See [Dockerfile.release](Dockerfile.release)
for specifics.

### Operator Mode Prerequisites

Operator mode requires access to a Kubernetes cluster running the Camel-K
operator and configured with the proper RBAC rules. See
[below](#ray-cluster-setup) for details.

At this time, the operator mode requires the Ray code to also run inside the same
Kubernetes cluster and requires the Camel-K client to be deployed to the Ray
nodes. We intend to lift these restrictions shortly.

Installing and using the Camel-K operator to deploy sources and sinks does not
require Java or Maven.

## Dynamic Dependencies

Camel-K is designed to pull dependencies dynamically from Maven Central at run
time. While it is possible to preload dependencies to support air-gapped
execution environments, Rayvens does not handle this yet.

## Ray Cluster Setup

The Rayvens [container image](https://quay.io/repository/ibm/rayvens) makes it
easy to deploy Rayvens-enabled Ray clusters to various container platforms. The
[rayvens-setup.sh](scripts/rayvens-setup.sh) script supports several
configurations out of the box: existing Kubernetes and OpenShift clusters,
development [Kind](https://kind.sigs.k8s.io) cluster, [IBM Cloud Code
Engine](https://www.ibm.com/cloud/code-engine). This script is distributed as
part of the Rayvens package and should typically have been added to the
executable search path by `pip install`. It is self-contained and therefore can
also be obtained directly:
```shell
curl -Lo rayvens-setup.sh https://raw.githubusercontent.com/project-codeflare/rayvens/main/scripts/rayvens-setup.sh
```
The full documentation for the script is available [here](docs/setup.md).

The script is provided for convenience. It is of course possible to setup a
Rayvens-enabled Ray cluster directly. We provide an example cluster
configuration in [cluster.yaml](scripts/cluster.yaml). This configuration file
is derived from Ray's
[example-full.yaml](https://github.com/ray-project/ray/blob/master/python/ray/autoscaler/kubernetes/example-full.yaml)
configuration file. The key changes are:
- use of Rayvens container image,
- RBAC enhancements to support the Camel-K operator,
- adjustments to resource requests and limits to account for the needs of Camel
  in local mode.

The generated and example configuration files also set `RAY_ADDRESS=auto` on the
head node, making it possible to run our example codes on the Ray cluster
unchanged.

### Kind Cluster Setup

To test Rayvens on a development Kubernetes cluster we recommend using
[Kind](https://kind.sigs.k8s.io).

We assume [Docker Desktop](https://www.docker.com/products/docker-desktop) is
installed. We assume Kubernetes support in Docker Desktop is turned off. We
assume [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) is installed.
Follow [instructions](https://kind.sigs.k8s.io/docs/user/quick-start) to install
the Kind client.

To create a Kind cluster and run a Rayvens-enabled Ray cluster on this Kind
cluster, run:
```shell
rayvens-setup.sh --kind --registry --kamel
```
The resulting cluster supports both local and operator modes. The command not
only initializes the Kind cluster but also launches a docker registry on port
5000 to be used by the Camel-K operator. To skip the registry and Camel-K setup,
run instead:
```shell
rayvens-setup.sh --kind
```
In this configuration, only local mode is supported. See [here](docs/setup.md)
for details.

The setup script produces a `rayvens.yaml` Ray cluster configuration file in the
current working directory. Try running on this cluster with:
```shell
ray submit rayvens.yaml rayvens/examples/stream.py
```

To take down the Kind cluster run:
```shell
kind delete cluster
```

To take down the docker registry run:
```shell
docker stop registry
docker rm registry
```

## Event Source Example

The [source.py](examples/source.py) example demonstrates how to process external
events with Rayvens.

First, we create a stream connected to an external event source:
```python
source = rayvens.Stream('http')
source_config = dict(
    kind='http-source',
    url='https://query1.finance.yahoo.com/v7/finance/quote?symbols=AAPL',
    period=3000)
source.add_source(source_config)
```

An event source configuration is a dictionary. The `kind` key specifies the
source type. Other keys vary. An `http-source` periodically makes a REST call to
the specified `url`. The `period` is expressed in milliseconds. The events
generated by this source are the bodies of the responses encoded as strings.

For convenience, the construction of the stream and addition of the source can
be combined into a single statement:
```python
source = rayvens.Stream('http', source_config=source_config)
```

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
        quote = payload['quoteResponse']['result'][0]['regularMarketPrice']
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
`source >> comparator.accept`. In other words, subscribing an actor `a` to a
stream is a shorthand for subscribing the `a.append` method of this actor to the
stream.

### Running the example

Run the example locally with:
```shell
python rayvens/examples/source.py
```

Run the example on Kind with:
```shell
ray submit rayvens.yaml rayvens/examples/source.py
```

When running in local mode, the Camel-K client has to download and cache
dependencies on first run from Maven Central. When running in operator mode, the
Camel-K operator is used to build and cache a container image for the source. In
both cases, the source may take a minute or more to start the first time. The
source should start in matter of seconds on subsequent runs (unless it is
scheduled to a different Ray worker in local mode, as the cache is not shared
across workers).

Rayvens manages the Camel processes and pods automatically and makes sure to
terminate them all when the main Ray program exits (normally or abnormally).

## Event Sink Example

The [slack.py](examples/slack.py) builds upon the previous example by pushing
the output messages to [Slack](https://slack.com).

In addition to the same source as before, it instantiates a sink:
```python
sink = rayvens.Stream('slack')
sink_config = dict(kind='slack-sink',
                   channel=slack_channel,
                   webhookUrl=slack_webhook)
sink.add_sink(sink_config)
```

For convenience, the construction of the stream and addition of the sink can be
combined into a single statement:
```python
sink = rayvens.Stream('slack', sink_config=sink_config)
```

This sink sends messages to Slack. It requires two configuration parameters that
must be provided as command-line parameters to the example program:
- the slack channel to publish to, e.g., `#test`, and
- a webhook url for this channel.

Please refer to the [Slack webhooks](https://api.slack.com/messaging/webhooks)
documentation for details on how to obtain these.

This example program includes a `Comparator` actor similar to the previous
example:
```python
@ray.remote
class Comparator:
    def __init__(self):
        self.last_quote = None

    def append(self, event):
        payload = json.loads(event)  # parse event string to json
        quote = payload['quoteResponse']['result'][0]['regularMarketPrice']
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

comparator = Comparator.remote()
```

In contrast to the previous example, we don't want to simply print messages to
the console from the comparator, but rather to produce a new stream of events
transformed by the comparator. To this aim, we construct an operator stream:
```python
operator = rayvens.Stream('comparator')
operator.add_operator(comparator)
```
or simply:
```python
operator = rayvens.Stream('comparator', operator=comparator)
```
Like any other stream, this operator stream can receive events and deliver
events to subscribers, but unlike earlier example, it applies a transformation
to the events. Concretely, it invokes the `append` method of the comparator
instance on each event and delivers the returned value to subscribers. By
convention, when `append` does not return a value, i.e., returns `None`, no
event is delivered to subscribers. In this example, the first source event does
not generate a Slack message.

We can then connect the source and sink via this operator using code:
```python
source >> operator >> sink
```
which is a shorthand for:
```python
source.send_to(operator)
operator.send_to(sink)
```

Like subscribers, the argument to the `add_operator` method may be a Python
function, a Ray task, a Ray actor, or a Ray actor method. Using an actor like
`comparator` is shorthand for the actor method `comparator.append`. Building an
operator stream from a Ray task is not recommended however as it may reorder
events arbitrarily.

### Running the example

We assume the `SLACK_CHANNEL` and `SLACK_WEBHOOK` environment variables contain
the necessary configuration parameters.

Run the example locally with:
```shell
python rayvens/examples/slack.py "$SLACK_CHANNEL" "$SLACK_WEBHOOK"
```

Run the example on Kind with:
```shell
ray submit rayvens.yaml rayvens/examples/slack.py "$SLACK_CHANNEL" "$SLACK_WEBHOOK"
```

## Combining Sources, Sinks, and Operators

A stream can have zero, one, or multiple sources, zero, one, or multiple sinks,
zero or one operator. For instance, rather than using three stream instances to
build our Slack example, we could do everything with a single stream as follows:
```python
source_config = dict(
    kind='http-source',
    url='https://query1.finance.yahoo.com/v7/finance/quote?symbols=AAPL',
    period=3000)

sink_config = dict(kind='slack-sink',
                   channel=slack_channel,
                   webhookUrl=slack_webhook)

operator = rayvens.Stream('comparator',
                          source_config=source_config,
                          operator=operator,
                          sink_config=sink_config)
```
This reduces the number of stream actors to one down from three and
significantly cut the number of remote invocations on the critical path hence
reducing latency.

## Further Reading

- Rayvens related blogs are published on [Medium](https://medium.com/codeflare).
- The `rayvens-setup.sh` script is documented in [setup.md](docs/setup.md).
- The configuration of the Camel sources and sinks is explained in
  [connectors.md](docs/connectors.md).

## License

Rayvens is an open-source project with an [Apache 2.0 license](LICENSE.txt).
