import ray
from ray import serve

from misc.events import kamel
from misc.events import execution
from misc.examples import slack_sink_common

import sys

ray.init(num_cpus=4)
client = serve.start()
route = "/toslack"
message = "Use Ray and Kamel in a kind cluster to print this to a kamel Slack"
"sink."

execMode = execution.Execution(location=execution.RayKamelExecLocation.CLUSTER)

slack_sink_common.exportSlackWebhook(sys.argv)

#
# Install kamel operator in the kind cluster created using the script
# in kamel subdirectory.
#

kamelImage = "docker.io/apache/camel-k:1.3.1"
publishRegistry = "registry:5000"
installInvocation = kamel.install(kamelImage,
                                  publishRegistry,
                                  localCluster=True,
                                  usingKind=True,
                                  insecureRegistry=True)

#
# Use kamel run to create the slack sink using the kamel operator.
#

integrationFiles = ["/home/ray/rayvens/misc/examples/kamel/slack.yaml"]

# List of environment variables to be used from current environment.
envVars = ["SLACK_WEBHOOK"]

# Note: careful with the names, for pod names, the integration name will be
# modified by kamel to replace underscores with dashes.
runInvocation = kamel.run(integrationFiles, "my-simple-integration", envVars)

#
# Start doing some work
#

execMode.setIntegrstionName("my-simple-integration")
slack_sink_common.sendMessageToSlackSink(client,
                                         message,
                                         route,
                                         execMode=execMode)

#
# Stop kamel sink.
#
kamel.delete(runInvocation)

#
# Uinstall the kamel operator from the cluster.
#
kamel.uninstall(installInvocation)
