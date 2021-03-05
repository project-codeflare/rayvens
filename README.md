# Rayvens

Rayvens augments [Ray](https://ray.io) with events. With Rayvens, Ray
applications can produce events, subscribe to event streams, and process events.
Rayvens leverages [Apache Camel](https://camel.apache.org) to make it possible
for data scientists to access hundreds data services with little effort.

## Setup Ray on Kind

Install [Kind](https://kind.sigs.k8s.io/docs/user/quick-start).

Clone this repository:
```sh
git clone https://github.ibm.com/solsa/rayvens.git
```

Setup a Ray cluster on a Kind cluster using a local docker registry:
```sh
./rayvens/scripts/start-kind.sh
```

To take down the cluster run:
```sh
kind delete cluster
```
