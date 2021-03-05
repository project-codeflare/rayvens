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
kamel install --registry-insecure --namespace ray --registry host.docker.internal:5000
