from enum import Enum
from rayvens.types import CamelOperatorMode
from rayvens.core.utils import utils


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
