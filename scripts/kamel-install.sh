#!/bin/sh

kubectl create serviceaccount kamel -n ray
kubectl create clusterrolebinding kamel --clusterrole=cluster-admin --serviceaccount=ray:kamel
kubectl run --rm -i -t kamel --image=apache/camel-k:1.3.1 --restart=Never --serviceaccount=kamel -n ray -- kamel install --force --registry-insecure --namespace ray --registry kamel-registry:5000
