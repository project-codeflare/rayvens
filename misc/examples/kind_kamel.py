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
# Use kamel run to create the slack sink using the kamel operator.
#
print("Length of active pod list after install: ", kubernetes.getNumActivePods())
print("Name of install pod is", kubernetes.getPodName(installInvocation))

integrationFiles = ["kamel/slack.yaml"]

# List of environment variables to be used from current environment.
envVars = ["SLACK_WEBHOOK"]

# Note: careful with the names, for pod names, the integration name will be
# modified by kamel to replace underscores with dashes.
runInvocation = kamel.run(integrationFiles, "my-simple-integration", envVars)

#
# Create service through which we can communicate with the kamel sink.
# The port of the service must be one of the ports externalized by the cluster.
# This is only required when the communication with the sink happen from
# outside the cluster.
#
serviceName = "kind-external-connector"
kubernetes.createExternalServiceForKamel(serviceName, "my-simple-integration")

print("Length of active pod list after kamel run: ",
      kubernetes.getNumActivePods())
print("Name of integration pod is", kubernetes.getPodName(runInvocation))

#
# Start doing some work
#

# Create a Kamel Backend and endpoint.
sinkBackend = kamel_backend.KamelBackend(client, mixedLocalCluster=True)
sinkBackend.createProxyEndpoint(
    "output_to_cluster_slack_sink", sinkEndpointRoute)

# Use endpoint to send data to the Ray Slack Sink.
answerAsStr = ""
for i in range(10):
    answerAsStr = sinkBackend.postToProxyEndpoint(
        "output_to_cluster_slack_sink", data + " Order number: %s" % i)
print(answerAsStr)

# Close proxy endpoint.
sinkBackend.removeProxyEndpoint("output_to_cluster_slack_sink")

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
kamel.uninstall(installInvocation)
print("Length of active pod list after uninstall: ",
      kubernetes.getNumActivePods())
