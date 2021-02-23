import ray
from ray import serve

from events import kamel_backend
from events import kamel

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
kamel.kamelInstall(
        kamelImage,
        publishRegistry,
        localCluster=True,
        usingKind=True,
        insecureRegistry=True)

#
# TODO: Use kamel run to create the slack sink using the kamel operator.
#

#
# Uinstall the kamel operator from the cluster.
#

kamel.kamelUninstall()
