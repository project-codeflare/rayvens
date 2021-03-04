#!/bin/sh

cd $(dirname "$0")

ray rsync-up cluster.yaml ../events .