import ray
from ray import serve

from events import kamel_backend
from events import kamel

from events import kubernetes

import time

ray.init(num_cpus=4)
client = serve.start()
sinkEndpointRoute = "/toslack"
data = "Use the kamel operator in a kind cluster to print this to a kamel Slack sink."

#
# Install kamel operator in the kind cluster created using the script
# in kamel subdirectory.
#

kamelImage = "localhost:5000/apache/camel-k:1.3.1"
publishRegistry = "registry:5000"
installInvocation = kamel.install(
        kamelImage,
        publishRegistry,
        localCluster=True,
        usingKind=True,
        insecureRegistry=True)

#
# TODO: Use kamel run to create the slack sink using the kamel operator.
#
print("Length of active pod list after install: ", kubernetes.getNumActivePods())
print("Name of install pod is", kubernetes.getPodName(installInvocation))

integrationFiles = ["kamel/slack.yaml"]

# Note: careful with the names, for pod names, the integration name will be
# modified by kamel to replace underscores with dashes.
runInvocation = kamel.run(integrationFiles, "my-simple-integration")

print("Length of active pod list after kamel run: ", kubernetes.getNumActivePods())
print("Name of integration pod is", kubernetes.getPodName(runInvocation))

time.sleep(10)

kamel.delete(runInvocation)

#
# Uinstall the kamel operator from the cluster.
#

kamel.uninstall(installInvocation)
print("Length of active pod list after uninstall: ", kubernetes.getNumActivePods())
