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

docker build .. -t localhost:5000/rayvens
docker push localhost:5000/rayvens
ray down cluster.yaml --yes
ray up cluster.yaml --no-config-cache --yes
