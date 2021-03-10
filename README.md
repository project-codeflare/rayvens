# Rayvens

[![Build Status](https://travis.ibm.com/solsa/rayvens.svg?token=U6PyxAbhWqm58XLxT7je&branch=master)](https://travis.ibm.com/solsa/rayvens)

Rayvens augments [Ray](https://ray.io) with events. With Rayvens, Ray
applications can produce events, subscribe to event streams, and process events.
Rayvens leverages [Apache Camel](https://camel.apache.org) to make it possible
for data scientists to access hundreds data services with little effort.

For example, one can periodically fetch data from a REST API with code:
```python
source_config = dict(
    kind='http-source',
    url='http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo',
    period=3000)
source = client.create_topic('http', source=source_config)
```

Publish messages to Slack with code:
```python
sink_config = dict(kind='slack-sink',
                   channel='#rayvens',
                   webhookUrl=os.getenv('RAYVENS_WEBHOOK'))
sink = client.create_topic('slack', sink=sink_config)
```

Connect the two together with code:
```python
source >> sink
```

Or do some event processing with code:
```python
source >> operator >> sink
```

## Setup Rayvens

These instructions have been tested on Big Sur and Ubuntu 18.04.4.

We recommend installing Python 3.8.7 using
[pyenv](https://github.com/pyenv/pyenv).

Install Ray and Ray Serve with Kubernetes support:
```shell
pip install --upgrade pip

# for osx
pip install https://s3-us-west-2.amazonaws.com/ray-wheels/master/6d5511cf8079f04d4f70ac724de8b62437adf0e7/ray-2.0.0.dev0-cp38-cp38-macosx_10_13_x86_64.whl

# for linux
pip install https://s3-us-west-2.amazonaws.com/ray-wheels/master/6d5511cf8079f04d4f70ac724de8b62437adf0e7/ray-2.0.0.dev0-cp38-cp38-manylinux2014_x86_64.whl

# for both
pip install "ray[serve]"
pip install kubernetes
```

Clone this repository and install Rayvens:
```shell
git clone https://github.ibm.com/solsa/rayvens.git
pip install -e rayvens
```

Try Rayvens:
```shell
python rayvens/examples/hello.py
```

Rayvens configures and uses [Ray
Serve](https://docs.ray.io/en/master/serve/index.html) to accept incoming
external events.

## A First Example

The [hello.py](examples/hello.py) file demonstrates an elementary Rayvens
program.
```python
import ray
import rayvens

ray.init()
client = rayvens.Client()

topic = client.create_topic('example')

topic >> print

topic << 'hello' << 'world'
```

This program initialize Ray and Rayvens and creates a `Topic`. Topics and events
are the core facilities offered by Rayvens. Topics bridge event publishers and
subscribers. Topic are currently implemented as Ray actors.

In this example, a subscriber is added to `topic` with the statement `topic >>
print`. This subscriber simply invokes the Python `print` method on every event
it receives. In general, subscribers can be Python callables, Ray tasks, or Ray
actors.

A couple of events are then published to `topic` using the syntax `topic <<
value`. As illustrate here, events are just arbitrary values in general, but of
course publishers and subscribers can agree on specific event schemas. The `<<`
operator has left-to-right associativity making it possible to send multiple
events with one statement.

Run this program with:
```shell
python rayvens/examples/hello.py
```
Observe the two events are delivered in order.

Other examples are provided in the [examples](examples) folder. See in
particular the [pubsub.py](examples/pubsub.py), [task.py](examples/task.py), and
[actor.py](examples/actor.py) examples for further discussions of in-order and
out-of-order event delivery.

## Setup Camel-K

To run Rayvens programs including Camel components, there are two choices:
- running Ray on the host with a local installation of the Camel-K client, Java,
  and Maven, or
- running Ray and Camel-K inside a Kubernetes cluster.

We expect to offer a "run anywhere" implementation in the near future.

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
creates a Kind cluster, installs Ray on this cluster as well as the [Camel-K
operator](https://camel.apache.org/camel-k/latest/architecture/operator.html).

Try your Ray cluster on Kind with:
```shell
ray submit rayvens/scripts/cluster.yaml rayvens/examples/pubsub.py
```

### Cluster.yaml

Our example [cluster.yaml](scripts/cluster.yaml) configuration file is derived from Ray's
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

First, we create a topic connected to an external event source:
```python
source_config = dict(
    kind='http-source',
    url='http://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=demo',
    period=3000)
source = client.create_topic('http', source=source_config)
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

    def ingest(self, event):
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

We then simply subscribe the `comparator` actor instance to the `source` topic.
```python
source >> comparator
```

By using a Ray actor to process events, we can implement stateful processing and
guarantee that events will be processed in order.

The `Comparator` class follows the convention that it accepts events by means of
a method named `ingest`. If for instance this method were to be named `accept`
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
sink = client.create_topic('slack', sink=sink_config)
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

    def ingest(self, event):
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

But in this case, the `ingest` method returns the status message instead of
printing it.

To make is possible to publish these messages to Slack, we first need to build a
topic around this actor using code:
```
operator = client.create_topic('comparator', operator=comparator)
```
This basically makes it possible for the comparator to act as an event source,
where the events produced are simply the stream of values returned from the
ingest method. Observe the `ingest` method does not have to produce an event for
every event it ingests.

We can then link the three topics using code:
```
source >> operator >> sink
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