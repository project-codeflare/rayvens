import ray
from ray import serve

from rayvens.core.camel_anywhere import kamel
from rayvens.core.camel_anywhere.mode import mode, RayKamelExecLocation
from rayvens.core.camel_anywhere.tests import slack_sink_common

import sys

ray.init(num_cpus=4)
client = serve.start()

route = "/toslack"
message = "Use Ray and Kamel in a kind cluster to print this to a kamel Slack"
"sink."

mode.location = RayKamelExecLocation.CLUSTER

slack_sink_common.exportSlackWebhook(sys.argv)

#
# Install kamel operator in the kind cluster created using the script
# in kamel subdirectory.
#

# kamelImage = "docker.io/apache/camel-k:1.3.1"
# publishRegistry = "registry:5000"
# installInvocation = kamel.install(kamelImage,
#                                   publishRegistry,
#                                   localCluster=True,
#                                   usingKind=True,
#                                   insecureRegistry=True)

#
# Use kamel run to create the slack sink using the kamel operator.
#

integrationFiles = [
    "/home/ray/rayvens/rayvens/core/camel/tests/kamel/slack.yaml"
]

# List of environment variables to be used from current environment.
envVars = ["SLACK_WEBHOOK"]

# Note: careful with the names, for pod names, the integration name will be
# modified by kamel to replace underscores with dashes.
runInvocation = kamel.run(integrationFiles, mode, "my-simple-integration",
                          envVars)

#
# Start doing some work.
#

mode.integrationName = "my-simple-integration"
slack_sink_common.sendMessageToSlackSink(client, message, route)

#
# Stop kamel sink.
#
kamel.delete(runInvocation)

#
# Uinstall the kamel operator from the cluster.
#
# kamel.uninstall(installInvocation)
