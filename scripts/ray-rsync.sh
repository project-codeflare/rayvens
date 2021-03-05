#!/bin/sh

cd $(python -c 'import os,sys;print(os.path.dirname(os.path.realpath(sys.argv[1])))' "$0")

ray rsync-up cluster.yaml ../rayvens .