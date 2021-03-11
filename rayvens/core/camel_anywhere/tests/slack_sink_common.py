from rayvens.core.camel_anywhere import kamel_backend
from rayvens.core.camel_anywhere.mode import mode
import os


def sendMessageToSlackSink(client, message, route):
    # Create a Kamel Backend and endpoint.
    sinkBackend = kamel_backend.KamelBackend(client, mode)
    sinkBackend.createProxyEndpoint(client, "output_to_ray_slack_sink", route)

    # Use endpoint to send data to the Ray Slack Sink.
    answerAsStr = ""
    for i in range(10):
        answerAsStr = sinkBackend.postToProxyEndpoint(
            client, "output_to_ray_slack_sink", message + " Part: %s" % i)
    print(answerAsStr)

    # Close proxy endpoint.
    sinkBackend.removeProxyEndpoint(client, "output_to_ray_slack_sink")


def exportSlackWebhook(args):
    if len(args) < 2:
        raise RuntimeError("usage: %s <slack_webhook>" % args[0])
    slack_webhook = args[1]
    os.environ['SLACK_WEBHOOK'] = slack_webhook
