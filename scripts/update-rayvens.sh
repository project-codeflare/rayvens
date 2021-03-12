#!/bin/sh

cd $(python -c 'import os,sys;print(os.path.dirname(os.path.realpath(sys.argv[1])))' "$0")

docker build .. -t localhost:5000/rayvens
docker push localhost:5000/rayvens
ray down cluster.yaml --yes
ray up cluster.yaml --no-config-cache --yes
