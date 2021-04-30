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

from enum import Enum
from rayvens.core import utils

# Port for internal communication inside the cluster.
internal_cluster_port = "80"

# Cluster source port.
internal_cluster_port_for_source = "8000"


class RayvensMode(Enum):
    # Ray and Kamel running locally.
    LOCAL = 1

    # Ray running locally, Kamel local running in a container in the cluster.
    MIXED_LOCAL = 2

    # Ray running locally, Kamel operator running in the cluster.
    MIXED_OPERATOR = 3

    # Ray in cluster, Kamel local running in a container in the cluster.
    CLUSTER_LOCAL = 4

    # Ray in cluster, Kamel operator running in the cluster.
    CLUSTER_OPERATOR = 5

    # Ray operator in cluster, Kamel local running in a container in cluster.
    OPERATOR_LOCAL = 6

    # Ray operator in cluster, Kamel operator running in the cluster.
    OPERATOR_OPERATOR = 7


class RunMode:
    def __init__(self, run_mode=RayvensMode.LOCAL):
        self.run_mode = run_mode
        self.namespace = "ray"
        self.transport = None

    def server_address(self, integration):
        return self._get_server_address(integration.integration_name,
                                        port=integration.port)

    def is_local(self):
        return self.run_mode == RayvensMode.LOCAL

    def is_mixed(self):
        return self.run_mode == RayvensMode.MIXED_OPERATOR

    def is_cluster(self):
        return self.run_mode == RayvensMode.CLUSTER_OPERATOR

    def _get_server_address(self,
                            integration_name,
                            serve_source=False,
                            port=None):
        if self.run_mode == RayvensMode.LOCAL:
            # Default setup: "http://0.0.0.0:8080"
            if port is None:
                raise RuntimeError('port is not specified')
            return f'http://localhost:{port}'
        if self.run_mode == RayvensMode.MIXED_OPERATOR:
            return "http://localhost:%s" % utils.externalized_cluster_port
        if self.run_mode == RayvensMode.CLUSTER_OPERATOR:
            if integration_name == "":
                raise RuntimeError("integration name is not set")
            if serve_source:
                return "http://%s.%s.svc.cluster.local:%s" % (
                    integration_name, self.namespace,
                    internal_cluster_port_for_source)
            return "http://%s.%s.svc.cluster.local:%s" % (
                integration_name, self.namespace, internal_cluster_port)
        raise RuntimeError("unreachable")


# Default execution mode.
mode = RunMode()
