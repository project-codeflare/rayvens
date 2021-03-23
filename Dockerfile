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

FROM rayproject/ray:9053be-py38

COPY --from=docker.io/apache/camel-k:1.3.1 /usr/local/bin/kamel /usr/local/bin/

RUN sudo apt-get update -qq \
    && sudo apt-get install -y -qq --no-install-recommends openjdk-11-jdk maven \
    && sudo rm -rf /var/lib/apt/lists/* \
    && sudo apt-get clean

COPY setup.py rayvens/
COPY rayvens rayvens/rayvens/

RUN sudo chown -R ray:users rayvens

RUN pip install confluent_kafka==1.6.0
RUN pip install -e ./rayvens
