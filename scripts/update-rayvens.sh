#!/bin/sh

docker build .. -t localhost:5000/rayvens
docker push localhost:5000/rayvens
ray down cluster.yaml --yes
ray up cluster.yaml --no-config-cache --yes
