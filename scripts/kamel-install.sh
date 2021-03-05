#!/bin/sh

kamel install --force --registry-insecure --namespace ray --registry "${DOCKER_REGISTRY:-host.docker.internal:5000}"
