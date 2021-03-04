#!/bin/sh

cd $(dirname "$0")

echo "--- starting private docker registry"
docker run -d --restart=always -p 5000:5000 --name registry registry:2

echo "--- starting kind cluster"
kind delete cluster
kind create cluster --config kind.yaml

echo "--- starting ray cluster"
ray up cluster.yaml --no-config-cache --yes

echo "--- installing kamel operator"
kamel install --registry-insecure --namespace ray --registry host.docker.internal:5000
