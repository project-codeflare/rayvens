#
# Copyright IBM Corporation 2021
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import ray
from ray import serve
from rayvens.core.camel_anywhere import kamel
from rayvens.core.camel_anywhere.tests import slack_sink_common
from rayvens.core.camel_anywhere.mode import mode
import time

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
integration_name = "my-simple-integration"
kamelInvocation = kamel.run(["kamel/slack.yaml"], mode, integration_name)

slack_sink_common.sendMessageToSlackSink(client, message, route,
                                         integration_name)
time.sleep(10)

# Kill all subprocesses associated with the kamel integration.
kamelInvocation.kill()
