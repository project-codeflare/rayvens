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

# Setup

We provide a self-contained [setup-rayvens.sh](../scripts/setup-rayvens.sh)
script to setup a Rayvens cluster on [Kubernetes](https://kubernetes.io),
[Openshift](https://www.openshift.com), or [IBM Cloud Code
Engine](https://www.ibm.com/cloud/code-engine). This script supports running
Rayvens on an existing Kubernetes cluster as well as creating a
[Kind](https://kind.sigs.k8s.io) development cluster to run Rayvens. The script
can optionally setup [Kafka](https://kafka.apache.org) and the [Camel-K
operator](https://operatorhub.io/operator/camel-k) on the cluster, as well as a
local container registry to host the container images produced by the Camel-K
operator. The script can generate a Ray cluster configuration yaml file or reuse
an existing one. The script defaults to using the released container image for
Rayvens but can also use a custom image. It can build a container image from a
local checkout of the Rayvens code as well.

```
./setup-rayvens.sh  --help
Configure and launch Rayvens-enabled Ray cluster on Kubernetes cluster.

Usage: setup-rayvens.sh [options]
    -c --config <rayens.yaml>       Ray cluster configuration file to use/generate (defaults to "rayvens.yaml" in current working directory)
    -n --namespace <namespace>      Kubernetes namespace to target (defaults to "ray")
    --image <image>                 Rayvens container image name (defaults to "quay.io/ibm/rayvens")
    --cpu <cpus>                    cpu quota for each Ray node (defaults to 1)
    --mem <mem>                     memory quota for each Ray node (defaults to 2Gi)
    --skip                          reuse existing cluster configuration file (skip generation)
    --ce                            skip service account setup on IBM Cloud Code Engine and use built-in namespace writer account
    --registry                      setup or reuse an insecure container registry running on localhost:5000
    --kamel                         install Kamel operator to cluster and enable on target namespace
    --kafka                         install Kafka to target namespace
    --kamel-options                 options to pass to Kamel install (to configure the container registry)
    --build                         build and push custom Rayvens container image from Rayvens source code in parent folder
    --example                       generate example file "example.py" in current working directory

    --kind                          setup a development Kind cluster on localhost instead of deploying to current Kubernetes context
                                    (destroy existing Kind cluster if any, set Kubernetes context to Kind)

    --dev                           shorthand for: --registry --build --image localhost:5000/rayvens --kind --kafka --kamel
```

## Kind Setup

To create a Kind cluster, a Ray cluster configuration file, deploy a Ray cluster
to the `ray` namespace on the Kind cluster, and produce an example Rayvens
program run:
```
./setup-rayvens.sh --kind --example
```
To try the example run:
```
ray submit rayvens.yaml example.py
```
This deployment does not include the Camel-K operator so it only supports
`local` mode.

To also deploy the Camel-K operator to the cluster run instead:
```
./setup-rayvens.sh --kind --example --registry --kamel
```
Try the example in `operator` mode with:
```
ray submit rayvens.yaml example.py operator
```
In this configuration, the script spawns a local container registry on the host
and configures the Camel-K operator to use this registry. An alternate registry
may be configured as illustrated below (IKS configuration).

The default settings for the name of the cluster configuration file, the Rayvens
container image to instantiate, the target namespace, the cpu and memory limits
for the ray nodes can be respectively overriding with flags `--config`,
`--image`, `--namespace`, `--cpu`, `--mem`.

The generation of the cluster configuration file can be skipped with flag
`--skip`. Use this flag to preserve manual tweaks to the configuration file. Be
aware that the script will only superficially validate the cluster configuration
in that case.

## Red Hat OpenShift on IBM Cloud Setup

To deploy Rayvens on OpenShift, first create a project:
```
oc new-project ray
```
To deploy Rayvens on the `ray` project:
```
./setup-rayvens.sh --kamel
```
The Camel-K operator is automatically configured to use the OpenShift container
registry.

## IBM Cloud Code Engine

To run Rayvens on Code Engine, first create and select a project:
```
ibmcloud ce project create --name rayvens
ibmcloud ce project select --name rayvens -k
```
Obtain the namespace for the project, for example:
```
kubectl get namespaces
NAME          STATUS   AGE
9fv37pz936r   Active   28d
```
Deploy Rayvens with:
```
./setup-rayvens.sh --ce --namespace 9fv37pz936r
```
The Camel-K operator cannot be deployed to Code Engine at this time so only
`local` mode is supported.

## IBM Cloud Kubernetes Service Setup

To deploy Rayvens on the `ray` namespace of an IKS cluster run:
```
./setup-rayvens.sh
```
Access to a container registry is required to deploy the Camel-K operator on
IKS. For instance, in order to use organization `myorg` on [Docker
Hub](https://hub.docker.com) run:
```
./setup-rayvens.sh --kamel --kamel-options "--registry docker.io --organization myorg --registry-auth-username myname --registry-auth-password mypassword"
```
