from ray import serve
import ray
from rayvens.core.camel_anywhere import kamel
from rayvens.core.camel_anywhere.tests import slack_sink_common

ray.init(num_cpus=4)

client = serve.start()

route = "/toslack"
message = "This local Slack sink has been created by Ray."

# TODO: Can we pass multiple yamls?
# TODO: Cloud version of this. Also handle kamel install.
# TODO: Explore running Ray on Cloud Engine with local head node and remote
# worker nodes.
# TODO: Can we auto-gen the yaml for these very simple sources and sinks.

# First we need to construct the kamel process which is going launch the
# actual kamel sink.
# Input is a list of tokens comprising the command.
kamelInvocation = kamel.localRun(["kamel/slack.yaml"])

slack_sink_common.sendMessageToSlackSink(client, message, route)

# Kill all subprocesses associated with the kamel integration.
kamelInvocation.kill.remote()
