#!/bin/sh

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

rayvens_version=0.2.0

config="rayvens.yaml"
namespace="ray"
image="quay.io/ibm/rayvens:$rayvens_version"
service_account="rayvens"
cpu="1"
mem="2G"

while [ -n "$1" ]; do
    case "$1" in
        -h|--help) help="1"; break;;
        -c|--config) shift; config="$1";;
        -n|--namespace) shift; namespace="$1";;
        --registry) registry="1"; options="--registry-insecure --registry registry:5000";;
        --build) build="1";;
        --image) shift; image="$1";;
        --kind) kind="1";;
        --kafka) kafka="1";;
        --kamel) kamel="1";;
        --kamel-options) shift; options="$1";;
        --skip) skip="1";;
        --ce) ce="1";;
        --cpu) shift; cpu=$1;;
        --mem) shift; mem=$1;;
        --example) example="1";;
        --preload) preload="1";;
        --version) version="1";;

        --dev)
            kind="1";
            kafka="1";
            registry="1";
            kamel="1";
            build="1";
            image="localhost:5000/rayvens";
            options="--registry-insecure --registry registry:5000"
            ;;
    esac
    shift
done

if [ -n "$ce" ]; then
  service_account="$namespace"-writer;
fi

if [ -n "$help" ]; then
    cat << EOF
Configure and launch Rayvens-enabled Ray cluster on Kubernetes cluster.

Usage: rayvens-setup.sh [options]
    -c --config <rayens.yaml>       Ray cluster configuration file to use/generate (defaults to "rayvens.yaml" in current working directory)
    -n --namespace <namespace>      Kubernetes namespace to target (defaults to "ray")
    --image <image>                 Rayvens container image name (defaults to "quay.io/ibm/rayvens")
    --cpu <cpus>                    cpu quota for each Ray node (defaults to 1)
    --mem <mem>                     memory quota for each Ray node (defaults to 2G)
    --skip                          reuse existing cluster configuration file (skip generation)
    --ce                            skip service account setup on IBM Cloud Code Engine and use built-in namespace writer account
    --registry                      setup or reuse an insecure container registry running on localhost:5000
    --kamel                         install Kamel operator to cluster and enable on target namespace
    --kafka                         install Kafka to target namespace
    --kamel-options                 options to pass to Kamel install (to configure the container registry)
    --build                         build and push custom Rayvens container image from Rayvens source code in parent folder
    --example                       generate example file "example.py" in current working directory
    --preload                       preload main camel jars into maven repository
    --version                       shows the version of this script

    --kind                          setup a development Kind cluster on localhost instead of deploying to current Kubernetes context
                                    (destroy existing Kind cluster if any, set Kubernetes context to Kind)

    --dev                           shorthand for: --registry --build --image localhost:5000/rayvens --kind --kafka --kamel
EOF
    exit 0
fi

if [ -n "$version" ]; then
  echo $rayvens_version
  exit 0
fi

if [ -n "$preload" ]; then
    tmp=$(mktemp -d)
    cat > "$tmp"/Preloader.java << EOF
/*
 * Copyright IBM Corporation 2021
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import org.apache.camel.BindToRegistry;
import org.apache.camel.Exchange;
import org.apache.camel.Processor;
import org.apache.camel.builder.RouteBuilder;

class Exit implements Processor {
  public void process(Exchange exchange) throws Exception {
    System.exit(0);
  }
}

public class Preloader extends RouteBuilder {
  @Override
  public void configure() throws Exception {
    from("timer:tick").to("bean:exit");
    from("platform-http:/null").to("http:null");
  }

  @BindToRegistry
  public Exit exit() {
    return new Exit();
  }
}
EOF
    kamel local run "$tmp"/Preloader.java --dependency mvn:org.apache.camel.quarkus:camel-quarkus-java-joor-dsl
    rm "$tmp"/Preloader.java
    rmdir "$tmp"
    exit 0
fi

if [ -z "$skip" ]; then
    echo "--- generating cluster configuration file"
    cat > "$config" << EOF
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

cluster_name: rayvens-cluster
max_workers: 2
upscaling_speed: 1.0
idle_timeout_minutes: 5
provider:
    type: kubernetes
    use_internal_ips: true
    namespace: $namespace
EOF
    if [ -z "$ce" ]; then
        cat >> "$config" << EOF
    autoscaler_service_account:
        apiVersion: v1
        kind: ServiceAccount
        metadata:
            name: $service_account
    autoscaler_role:
        kind: Role
        apiVersion: rbac.authorization.k8s.io/v1
        metadata:
            name: $service_account
        rules:
            - apiGroups: [""]
              resources: ["pods", "pods/status", "pods/exec", "pods/log"]
              verbs: ["get", "watch", "list", "create", "delete", "patch"]
            - apiGroups: ["camel.apache.org"]
              resources: ["integrations", "integrations/status"]
              verbs: ["*"]
    autoscaler_role_binding:
        apiVersion: rbac.authorization.k8s.io/v1
        kind: RoleBinding
        metadata:
            name: $service_account
        subjects:
            - kind: ServiceAccount
              name: $service_account
        roleRef:
            kind: Role
            name: $service_account
            apiGroup: rbac.authorization.k8s.io
EOF
    fi
    cat >> "$config" << EOF
    services:
        - apiVersion: v1
          kind: Service
          metadata:
              name: rayvens-cluster-head
          spec:
              selector:
                  component: rayvens-cluster-head
              ports:
                  - name: client
                    protocol: TCP
                    port: 10001
                    targetPort: 10001
                  - name: ray-serve
                    protocol: TCP
                    port: 8000
                    targetPort: 8000
                  - name: dashboard
                    protocol: TCP
                    port: 8265
                    targetPort: 8265
head_node_type: head_node
available_node_types:
    worker_node:
        min_workers: 0
        max_workers: 2
        node_config:
            apiVersion: v1
            kind: Pod
            metadata:
                generateName: rayvens-cluster-worker-
            spec:
                serviceAccountName: $service_account
                restartPolicy: Never
                volumes:
                    - name: dshm
                      emptyDir:
                          medium: Memory
                    - name: podinfo
                      downwardAPI:
                          items:
                              - path: "labels"
                                fieldRef:
                                    fieldPath: metadata.labels
                              - path: "name"
                                fieldRef:
                                    fieldPath: metadata.name
                              - path: "namespace"
                                fieldRef:
                                    fieldPath: metadata.namespace
                containers:
                    - name: ray-node
                      imagePullPolicy: Always
                      image: $image
                      command: ["/bin/bash", "-c", "--"]
                      args: ["trap : TERM INT; sleep infinity & wait;"]
                      volumeMounts:
                          - mountPath: /dev/shm
                            name: dshm
                          - name: podinfo
                            mountPath: /etc/podinfo
                      resources:
                          requests:
                              cpu: $cpu
                              memory: $mem
                          limits:
                              cpu: $cpu
                              memory: $mem
    head_node:
        min_workers: 0
        max_workers: 0
        node_config:
            apiVersion: v1
            kind: Pod
            metadata:
                generateName: rayvens-cluster-head-
                labels:
                    component: rayvens-cluster-head
            spec:
                serviceAccountName: $service_account
                restartPolicy: Never
                volumes:
                    - name: dshm
                      emptyDir:
                          medium: Memory
                    - name: podinfo
                      downwardAPI:
                          items:
                              - path: "labels"
                                fieldRef:
                                    fieldPath: metadata.labels
                              - path: "name"
                                fieldRef:
                                    fieldPath: metadata.name
                              - path: "namespace"
                                fieldRef:
                                    fieldPath: metadata.namespace
                containers:
                    - name: ray-node
                      image: $image
                      command: ["/bin/bash", "-c", "--"]
                      args: ["trap : TERM INT; sleep infinity & wait;"]
                      ports:
                          - containerPort: 6379
                          - containerPort: 10001
                          - containerPort: 8265
                      volumeMounts:
                          - mountPath: /dev/shm
                            name: dshm
                          - name: podinfo
                            mountPath: /etc/podinfo
                      resources:
                          requests:
                              cpu: $cpu
                              memory: $mem
                          limits:
                              cpu: $cpu
                              memory: $mem
                      env:
                          - name: RAY_ADDRESS
                            value: auto
head_start_ray_commands:
    - ray stop
    - ulimit -n 65536; ray start --head --autoscaling-config=~/ray_bootstrap_config.yaml --dashboard-host 0.0.0.0
worker_start_ray_commands:
    - ray stop
    - ulimit -n 65536; ray start --address=\$RAY_HEAD_IP:6379
EOF
else
    echo "--- skipping generation of cluster configuration file"
    if [ ! -f "$config" ]; then
        echo "ERROR: cannot find cluster configuration file $config in $PWD"
        exit 1
    fi
    grep "namespace: *$namespace" cluster.yaml > /dev/null || echo "WARNING: cannot find namespace $namespace in configuration file"
    grep "image: *$image" cluster.yaml > /dev/null || echo "WARNING: cannot fine image $image in configuration file"
fi

if [ -n "$registry" ]; then
    echo "--- starting local container registry"
    docker run -d --restart=always -p 5000:5000 --name registry registry:2
fi

if [ -n "$kind" ]; then
    echo "--- starting Kind cluster"
    tmp=$(mktemp)
    cat > "$tmp" << EOF
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

kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
containerdConfigPatches:
  - |-
    [plugins."io.containerd.grpc.v1.cri".registry.mirrors."localhost:5000"]
      endpoint = ["http://registry:5000"]
    [plugins."io.containerd.grpc.v1.cri".registry.mirrors."registry:5000"]
      endpoint = ["http://registry:5000"]
nodes:
  - role: control-plane
    extraPortMappings:
      - containerPort: 31093
        hostPort: 31093
        protocol: TCP
      - containerPort: 31095
        hostPort: 31095
        protocol: TCP
EOF
    kind delete cluster
    kind create cluster --config "$tmp"
    rm "$tmp"
    if [ -n "$registry" ]; then
        docker network connect kind registry
    fi
fi

if [ -n "$build" ]; then
    echo "--- building the Rayvens image"
    docker build .. -t "$image"
    docker push "$image"
fi

if [ -z "$ce" ]; then
    echo "--- creating namespace"
    kubectl create namespace "$namespace"
fi

if [ -n "$kafka" ]; then
    echo "--- installing Kafka"
    tmp=$(mktemp)
    cat > "$tmp" << EOF
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

apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: zookeeper
spec:
  replicas: 1
  selector:
    matchLabels:
      name: zookeeper
  serviceName: zookeeper
  template:
    metadata:
      labels:
        name: zookeeper
    spec:
      containers:
        - name: zk
          image: docker.io/zookeeper:3.5
          ports:
            - name: zookeeper
              containerPort: 2181
            - name: server
              containerPort: 2888
            - name: leader-election
              containerPort: 3888
          livenessProbe:
            tcpSocket:
              port: 2181
          readinessProbe:
            exec:
              command:
                - /bin/bash
                - -c
                - "echo ruok | nc -w 1 localhost 2181 | grep imok"
          env:
            - name: ZOO_4LW_COMMANDS_WHITELIST
              value: "srvr,ruok"
---
apiVersion: v1
kind: Service
metadata:
  name: zookeeper
spec:
  type: ClusterIP
  clusterIP: None
  selector:
    name: zookeeper
  ports:
    - name: zookeeper
      port: 2181
      targetPort: 2181
    - name: server
      port: 2888
      targetPort: 2888
    - name: leader-election
      port: 3888
      targetPort: 3888
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: kafka
spec:
  replicas: 1
  selector:
    matchLabels:
      name: kafka
  serviceName: kafka
  template:
    metadata:
      labels:
        name: kafka
    spec:
      initContainers:
        - name: wait-for-zookeeper
          image: busybox
          command:
            [
              "sh",
              "-c",
              'result=1; until [ \$result -eq 0 ]; do OK=\$(echo ruok | nc -w 1 zookeeper 2181); if [ "\$OK" == "imok" ]; then result=0; echo "zookeeper returned imok!"; else echo waiting for zookeeper to be ready; sleep 1; fi; done; echo "Success: zookeeper is up"',
            ]
      containers:
        - name: kafka
          image: docker.io/wurstmeister/kafka:2.13-2.6.0
          ports:
            - name: kafka-internal
              containerPort: 9092
            - name: kafka-external
              containerPort: 9093
          readinessProbe:
            initialDelaySeconds: 10
            timeoutSeconds: 5
            periodSeconds: 10
            exec:
              command:
                - /opt/kafka/bin/kafka-topics.sh
                - localhost:9092
                - --version
          env:
            - name: HOSTNAME_COMMAND
              value: hostname -f
            - name: KAFKA_LISTENER_SECURITY_PROTOCOL_MAP
              value: INCLUSTER:PLAINTEXT,EXTERNAL:PLAINTEXT
            - name: KAFKA_LISTENERS
              value: INCLUSTER://:9092,EXTERNAL://:9093
            - name: KAFKA_ADVERTISED_LISTENERS
              value: INCLUSTER://_{HOSTNAME_COMMAND}:9092,EXTERNAL://localhost:31093
            - name: KAFKA_INTER_BROKER_LISTENER_NAME
              value: INCLUSTER
            - name: KAFKA_ZOOKEEPER_CONNECT
              value: zookeeper:2181
            - name: KAFKA_AUTO_CREATE_TOPICS_ENABLE
              value: "true"
            - name: KAFKA_PORT
              value: "9092"
---
apiVersion: v1
kind: Service
metadata:
  name: kafka
spec:
  type: NodePort
  selector:
    name: kafka
  ports:
    - name: kafka-internal
      port: 9092
      targetPort: 9092
    - name: kafka-external
      port: 9093
      targetPort: 9093
      nodePort: 31093
EOF
    kubectl apply -n "$namespace" -f "$tmp"
    rm "$tmp"
fi

if [ -n "$kamel" ]; then
    echo "--- installing Kamel operator"
    kubectl create serviceaccount kamel -n "$namespace"
    kubectl create clusterrolebinding kamel --clusterrole=cluster-admin --serviceaccount="$namespace":kamel
    kubectl run --rm -i -t kamel --image=apache/camel-k:1.5.0 --restart=Never --serviceaccount=kamel -n "$namespace" -- \
        kamel install --force $(echo "$options")
    kubectl delete clusterrolebinding kamel
    kubectl delete serviceaccount kamel -n "$namespace"
fi

echo "--- starting Ray cluster"
ray up "$config" --no-config-cache --yes

if [ -n "$example" ]; then
    echo "--- generating example file"
    echo "--- try to run: ray submit $config example.py"
    cat > example.py << EOF
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

import asyncio
import json
import os
import ray
import rayvens
import sys

ray.init()
rayvens.init(mode=sys.argv[1] if len(sys.argv) > 1 else 'local')

source_config = dict(
    kind='http-source',
    url='https://query1.finance.yahoo.com/v7/finance/quote?symbols=AAPL',
    period=3000)
source = rayvens.Stream('http', source_config=source_config)


@ray.remote
class Counter:
    def __init__(self):
        self.count = 0
        self.ready = asyncio.Event()

    def append(self, event):
        print('AAPL is', json.loads(event)[0]['quoteResponse']['result'][0]['regularMarketPrice'])
        self.count += 1
        if self.count > 5:
            self.ready.set()

    async def wait(self):
        await self.ready.wait()


counter = Counter.remote()

source >> counter

ray.get(counter.wait.remote(), timeout=180)
EOF
fi
