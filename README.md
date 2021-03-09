# Rayvens

Rayvens augments [Ray](https://ray.io) with events. With Rayvens, Ray
applications can produce events, subscribe to event streams, and process events.
Rayvens leverages [Apache Camel](https://camel.apache.org) to make it possible
for data scientists to access hundreds data services with little effort.

## Setup Rayvens

These instructions have been tested on Big Sur.

We recommend installing Python 3.8.7 using
[pyenv](https://github.com/pyenv/pyenv).

Install Ray and Ray Serve with Kubernetes support:
```shell
pip install --upgrade pip
pip install https://s3-us-west-2.amazonaws.com/ray-wheels/latest/ray-2.0.0.dev0-cp38-cp38-macosx_10_13_x86_64.whl
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

topic << 'hello'
topic << 'world'
```

This program initialize Ray and Rayvens and creates a `Topic`. Topics and events
are the core facility offered by Rayvens. Topics bridge event publishers and
subscribers.

In this example, a subscriber is added to `topic` with the statement `topic >>
print`. This subscriber simply invokes the Python `print` method on every event
it receives. In general, subscribers can be Python callables, ray tasks, or ray
actors.

A couple of events are then published to `topic` using the syntax `topic <<
value`. As illustrate here, events are just arbitrary values in general, but of
course publishers and subscribers can agree on specific event schemas.

Run this program with:
```shell
python rayvens/examples/hello.py
```
Observe the two events are delivered in order.

Other examples of subscribers are provided in the [examples](examples) folder.
See in particular the [task.py](examples/task.py) and
[actor.py](examples/actor.py) examples for further discussions of in-order and
out-of-order event delivery.

## Setup Camel-K

To run Rayvens programs including Camel components, there are two choices:
- running Ray on the host with a local installation of the Camel-K client, Java,
  and Maven, or
- running Ray and Camel-K inside a Kubernetes cluster.

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
ray submit rayvens/scripts/cluster.yaml rayvens/examples/hello.py 
```

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

# License

Rayvens is an open-source project with an [Apache 2.0 license](LICENSE.txt). 