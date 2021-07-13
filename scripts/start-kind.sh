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

cd $(python -c 'import os,sys;print(os.path.dirname(os.path.realpath(sys.argv[1])))' "$0")

echo "--- starting private docker registry"
docker run -d --restart=always -p 5000:5000 --name registry registry:2

echo "--- building the rayvens image"
docker build .. -t localhost:5000/rayvens
docker push localhost:5000/rayvens

echo "--- starting kind cluster"
kind delete cluster
kind create cluster --config kind.yaml
docker network connect kind registry

echo "--- installing kafka"
kubectl create namespace ray
kubectl apply -n ray -f kafka.yaml

echo "--- installing kamel operator"
kubectl create serviceaccount kamel -n ray
kubectl create clusterrolebinding kamel --clusterrole=cluster-admin --serviceaccount=ray:kamel
kubectl run --rm -i -t kamel --image=apache/camel-k:1.5.0 --restart=Never --serviceaccount=kamel -n ray -- \
    kamel install --registry-insecure --namespace ray --registry registry:5000
kubectl delete clusterrolebinding kamel
kubectl delete serviceaccount kamel -n ray

echo "--- starting ray cluster"
ray up cluster.yaml --no-config-cache --yes
