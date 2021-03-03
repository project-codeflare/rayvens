import ray
from events import kamel_backend
from events import kamel
from events import invocation
from ray import serve
import requests
import subprocess
import time

ray.init(num_cpus=4)
client = serve.start()
sinkEndpointRoute = "/toslack"
data = "This Slack sink has been created by Ray."

# TODO: Can we pass multiple yamls?
# TODO: Cloud version of this. Also handle kamel install.
# TODO: Explore running Ray on Cloud Engine with local head node and remote worker nodes.
# TODO: Can we auto-gen the yaml for these very simple sources and sinks.

# First we need to construct the kamel process which is going launch the actual kamel sink.
# Input is a list of tokens comprising the command.
command = ["kamel/slack.yaml"]
kamelInvocation = kamel.localRun(command)

# === Start doing some work ===

# Create a Kamel Backend and endpoint.
sinkBackend = kamel_backend.KamelBackend(client)
sinkBackend.createProxyEndpoint("output_to_ray_slack_sink", sinkEndpointRoute)

# Use endpoint to send data to the Ray Slack Sink.
answerAsStr = ""
for i in range(10):
    answerAsStr = sinkBackend.postToProxyEndpoint(
        "output_to_ray_slack_sink", data + " Order number: %s" % i)
print(answerAsStr)

# Close proxy endpoint.
sinkBackend.removeProxyEndpoint("output_to_ray_slack_sink")

# === Stop doing some work ===

# Kill all subprocesses associated with the kamel integration.
kamelInvocation.kill.remote()
