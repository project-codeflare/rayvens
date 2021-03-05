#!/bin/sh

cd $(python -c 'import os,sys;print(os.path.dirname(os.path.realpath(sys.argv[1])))' "$0")

echo "--- starting private docker registry"
docker run -d --restart=always -p 5000:5000 --name registry registry:2

echo "--- starting kind cluster"
kind delete cluster
kind create cluster --config kind.yaml

echo "--- starting ray cluster"
ray up cluster.yaml --no-config-cache --yes

echo "--- installing kamel operator"
kubectl create namespace ray
kubectl create serviceaccount kamel -n ray
kubectl create clusterrolebinding kamel --clusterrole=cluster-admin --serviceaccount=ray:kamel
kubectl run --rm -i -t kamel --image=apache/camel-k:1.3.1 --restart=Never --serviceaccount=kamel -n ray -- \
    kamel install --force --registry-insecure --namespace ray --registry host.docker.internal:5000
