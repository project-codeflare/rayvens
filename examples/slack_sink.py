import ray
from events import kamel_backend
from events import invocation
from ray import serve
import requests
import subprocess
import time

ray.init(num_cpus=4)
# client = serve.start()
sinkEndpointRoute = "/toslack"
data = "Test Slack output!"

# TODO: Can we pass multiple yamls?
# TODO: Cloud version of this. Also handle kamel install.
# TODO: Explore running Ray on Cloud Engine with local head node and remote worker nodes.
# TODO: Can we auto-gen the yaml for these very simple sources and sinks.

# First we need to construct the kamel process which is going launch the actual kamel sink.
# Input is a list of tokens comprising the command.
command = ["kamel", "local", "run", "kamel/slack.yaml"]

# TODO: Explore merging topics and invocation actors. Listen on a topic and attach an external source/sink to it.
kamelInvocation = invocation.KamelInvocationActor.remote(command)

# Wait for kamel command to finish launching the integration.
kamelIsReady = ray.get(kamelInvocation.isKamelReady.remote())

print("Kamel is ready:", kamelIsReady)

# Do some work.

# Kill all subprocesses associated with the kamel integration.
kamelInvocation.kill.remote()

# # client.create_backend("kamel_slack_backend", kamel_backend.KamelSinkHandler)
# sinkBackend = kamel_backend.KamelBackend(client)

# # client.create_external_endpoint("output_to_slack", backend="kamel_slack_backend", route=sinkEndpointRoute, methods=["POST"])
# sinkBackend.createProxyEndpoint("output_to_slack", sinkEndpointRoute)

# answerAsStr = ""
# for i in range(10):
#     answerAsStr = sinkBackend.postToProxyEndpoint("output_to_slack", data + " Order number: %s" % i)
# print(answerAsStr)

# sinkBackend.removeProxyEndpoint("output_to_slack")