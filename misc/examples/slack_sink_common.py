from misc.events import kamel_backend
from misc.events import execution
import os


def sendMessageToSlackSink(client, message, route, execMode=None):
    if execMode is None:
        execMode = execution.Execution()

    # Create a Kamel Backend and endpoint.
    sinkBackend = kamel_backend.KamelBackend(client, execMode)
    sinkBackend.createProxyEndpoint("output_to_ray_slack_sink", route)

    # Use endpoint to send data to the Ray Slack Sink.
    answerAsStr = ""
    for i in range(10):
        answerAsStr = sinkBackend.postToProxyEndpoint(
            "output_to_ray_slack_sink", message + " Part: %s" % i)
    print(answerAsStr)

    # Close proxy endpoint.
    sinkBackend.removeProxyEndpoint("output_to_ray_slack_sink")


def exportSlackWebhook(args):
    if len(args) < 2:
        raise RuntimeError("usage: %s <slack_webhook>" % args[0])
    slack_webhook = args[1]
    os.environ['SLACK_WEBHOOK'] = slack_webhook