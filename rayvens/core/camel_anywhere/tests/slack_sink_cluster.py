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

# List of environment variables to be used from current environment.
envVars = ["SLACK_WEBHOOK"]
integrationFiles = [
    "/home/ray/rayvens/rayvens/core/camel_anywhere/tests/kamel/slack.yaml"
]
integration_name = "my-simple-integration"

# Note: careful with the names, for pod names, the integration name will be
# modified by kamel to replace underscores with dashes.
runInvocation = kamel.run(integrationFiles,
                          mode,
                          integration_name,
                          envVars=envVars)

#
# Start doing some work.
#
slack_sink_common.sendMessageToSlackSink(client, message, route,
                                         integration_name)

#
# Stop kamel sink.
#
kamel.delete(runInvocation)

#
# Uinstall the kamel operator from the cluster.
#
# kamel.uninstall(installInvocation)
