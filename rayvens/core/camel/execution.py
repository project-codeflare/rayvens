from rayvens.core.camel import utils
from enum import Enum

# Enum for capturing the location of the Kamel execution.


class KamelExecMode(Enum):
    # The Kamel operator can only be run on the Ray head node.
    OPERATOR_HEAD_NODE = 1

    # Kamel operator can run anywhere in the cluster.
    OPERATOR_ANYWHERE = 2

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
                 kamelExecMode=KamelExecMode.OPERATOR_ANYWHERE):
        self.location = location
        self.kamelExecMode = kamelExecMode
        self.integrationName = ""
        self.namespace = "ray"

    def setIntegrstionName(self, integrationName):
        self.integrationName = integrationName

    def setNamespace(self, namespace):
        self.namespace = namespace

    def getNamespace(self):
        return self.namespace

    def getQuarkusHTTPServer(self):
        if self.location == RayKamelExecLocation.LOCAL:
            return "http://0.0.0.0:8080"
        if self.location == RayKamelExecLocation.MIXED:
            return "http://localhost:%s" % utils.externalizedClusterPort
        if self.location == RayKamelExecLocation.CLUSTER:
            if self.integrationName == "":
                raise RuntimeError("integration name is not set")
            return "http://%s.%s.svc.cluster.local:%s" % (
                self.integrationName, self.namespace,
                utils.internalClusterPort)
        raise RuntimeError("unreachable")

    def isLocal(self):
        return self.location == RayKamelExecLocation.LOCAL

    def isMixed(self):
        return self.location == RayKamelExecLocation.MIXED

    def isCluster(self):
        return self.location == RayKamelExecLocation.CLUSTER


# Default execution mode.
mode = Execution()
