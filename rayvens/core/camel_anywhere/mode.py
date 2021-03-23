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
from rayvens.core.utils import utils


class CamelOperatorMode(Enum):
    # The Kamel operator can only be run on the Ray head node.
    HEAD_NODE = 1

    # Kamel operator can run anywhere in the cluster.
    ANY_NODE = 2

    # No Kamel operator needed just kamel running local command in a container.
    CONTAINERIZED = 3


class RayKamelExecLocation(Enum):
    # Ray and Kamel running locally.
    LOCAL = 1

    # Ray running locally, Kamel running in the cluster.
    MIXED = 2

    # Ray and Kamel running in the cluster.
    CLUSTER = 3


class Execution:
    def __init__(self,
                 location=RayKamelExecLocation.LOCAL,
                 kamelExecMode=CamelOperatorMode.ANY_NODE):
        self.location = location
        self.kamelExecMode = kamelExecMode
        self.connector = 'http'
        self.namespace = "ray"

    def setNamespace(self, namespace):
        self.namespace = namespace

    def getNamespace(self):
        return self.namespace

    def getQuarkusHTTPServer(self, integration_name, serve_source=False):
        if self.location == RayKamelExecLocation.LOCAL:
            return "http://0.0.0.0:8080"
        if self.location == RayKamelExecLocation.MIXED:
            return "http://localhost:%s" % utils.externalizedClusterPort
        if self.location == RayKamelExecLocation.CLUSTER:
            if integration_name == "":
                raise RuntimeError("integration name is not set")
            if serve_source:
                return "http://%s.%s.svc.cluster.local:%s" % (
                    integration_name, self.namespace,
                    utils.internalClusterPortForSource)
            return "http://%s.%s.svc.cluster.local:%s" % (
                integration_name, self.namespace, utils.internalClusterPort)
        raise RuntimeError("unreachable")

    def isLocal(self):
        return self.location == RayKamelExecLocation.LOCAL

    def isMixed(self):
        return self.location == RayKamelExecLocation.MIXED

    def isCluster(self):
        return self.location == RayKamelExecLocation.CLUSTER

    def hasHTTPConnector(self):
        return self.connector == 'http'

    def hasRayServeConnector(self):
        return self.connector == 'ray-serve'


# Default execution mode.
mode = Execution()
