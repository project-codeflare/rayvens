import ray
from ray import serve

from rayvens.core.camel_anywhere import kamel
from rayvens.core.camel_anywhere.mode import mode, RayKamelExecLocation
from rayvens.core.camel_anywhere import kubernetes
from rayvens.core.camel_anywhere.tests import slack_sink_common

ray.init(num_cpus=4)
client = serve.start()
route = "/toslack"
message = "While Ray runs locally, use the kamel operator in a kind cluster to"
"print this to a kamel Slack sink."

mode.location = RayKamelExecLocation.MIXED

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
# print("Length of active pod list after install: ",
#       kubernetes.getNumActivePods())
# print("Name of install pod is", kubernetes.getPodName(installInvocation))

# List of environment variables to be used from current environment.
envVars = ["SLACK_WEBHOOK"]
integrationFiles = ["kamel/slack.yaml"]
integration_name = "my-simple-integration"

# Note: careful with the names, for pod names, the integration name will be
# modified by kamel to replace underscores with dashes.
runInvocation = kamel.run(integrationFiles, mode, integration_name, envVars)

#
# Create service through which we can communicate with the kamel sink.
# The port of the service must be one of the ports externalized by the cluster.
# This is only required when the communication with the sink happen from
# outside the cluster.
#
serviceName = "kind-external-connector"
kubernetes.createExternalServiceForKamel(serviceName, integration_name)

print("Length of active pod list after kamel run: ",
      kubernetes.getNumActivePods())
print("Name of integration pod is", kubernetes.getPodName(runInvocation))

#
# Start doing some work
#
slack_sink_common.sendMessageToSlackSink(client, message, route,
                                         integration_name)

#
# Stop kubectl service for externalizing the sink listener.
#
kubernetes.deleteService(serviceName)

#
# Stop kamel sink.
#
kamel.delete(runInvocation)

#
# Uinstall the kamel operator from the cluster.
#
# kamel.uninstall(installInvocation)
print("Length of active pod list after uninstall: ",
      kubernetes.getNumActivePods())
