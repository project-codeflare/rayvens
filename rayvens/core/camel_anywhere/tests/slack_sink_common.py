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

from rayvens.core.camel_anywhere import kamel_backend
from rayvens.core.camel_anywhere.mode import mode
import os


def sendMessageToSlackSink(client, message, route, integration_name):
    # Create a Kamel Backend and endpoint.
    sinkBackend = kamel_backend.KamelBackend(client, mode)
    endpoint_name = "output_to_ray_slack_sink"
    sinkBackend.createProxyEndpoint(client, endpoint_name, route,
                                    integration_name)

    # Use endpoint to send data to the Ray Slack Sink.
    answerAsStr = ""
    for i in range(10):
        answerAsStr = sinkBackend.postToProxyEndpoint(
            client, endpoint_name, message + " Part: %s" % i)
    print(answerAsStr)

    # Close proxy endpoint.
    sinkBackend.removeProxyEndpoint(client, endpoint_name)


def exportSlackWebhook(args):
    if len(args) < 2:
        raise RuntimeError("usage: %s <slack_webhook>" % args[0])
    slack_webhook = args[1]
    os.environ['SLACK_WEBHOOK'] = slack_webhook
