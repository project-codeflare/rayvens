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

#
# Run modes.
#
# Note: Kamel Operator) needs a cluster to run in.
# Note: Ray Operator) needs a cluster to run in.
#
# Legend:
#
#  clstr i.e. cluster : Kamel/Ray run inside or outside the cluster.
#  oprtr i.e. operator: Kamel/Ray run using their Kubernetes operator
#                       implementation.
#
#  Running outside the cluster means that no operator can be used hence
#  the use of the `-` for those table entries.
#  When running inside the cluster (i.e. clstr:yes) then there is a choice:
#  - use the operator (i.e. oprtr:yes)
#  - run local to the container (i.e. oprtr:no). For kamel this is
#  equivalent to doing a `kamel local run` inside the container.
#
#  Connector types between sources/sinks and Ray:
#     - RS   : Ray Serve for sources and HTTP requests for sinks.
#     - P2P  : HTTP requests on both source and sink side.
#     - K    : Kafka for both sources and sinks.
#
# Mode              |      Ray      |     Kamel     ||   Transport
#                   | clstr | oprtr | clstr | oprtr || RS | P2P | K |
# ------------------|-------|-------|-------|-------||----|-----|---|
# local             | no    | -     | no    | -     ||    | v   |   |
# ------------------|-------|-------|-------|-------||----|-----|---|
# mixed.local       | no    | -     | yes   | no    ||    |     |   |
# mixed.operator    | no    | -     | yes   | yes   ||    | v   |   |
# ------------------|-------|-------|-------|-------||----|-----|---|
# cluster.local     | yes   | no    | yes   | no    ||    | v   | v |
# cluster.operator  | yes   | no    | yes   | yes   ||    | v   |   |
# operator.local    | yes   | yes   | yes   | no    ||    |     |   |
# operator.operator | yes   | yes   | yes   | yes   ||    |     |   |
#
