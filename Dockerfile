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

ARG base_image=rayproject/ray:1.13.0-py38
FROM ${base_image}

COPY --from=docker.io/apache/camel-k:1.5.1 /usr/local/bin/kamel /usr/local/bin/

RUN sudo apt-get update \
    && sudo apt-get install -y --no-install-recommends openjdk-11-jdk maven \
    && sudo rm -rf /var/lib/apt/lists/* \
    && sudo apt-get clean

COPY --chown=ray:users scripts/Preloader.java .
RUN kamel local run Preloader.java --dependency mvn:org.apache.camel.quarkus:camel-quarkus-java-joor-dsl; rm Preloader.java

COPY --chown=ray:users setup.py rayvens/
COPY --chown=ray:users rayvens rayvens/rayvens/
COPY --chown=ray:users scripts/rayvens-setup.sh rayvens/scripts/

RUN pip install -e ./rayvens
