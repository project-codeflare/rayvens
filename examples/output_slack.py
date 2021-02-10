import ray
from events import kamel_backend
from events import topics
from ray import serve
import requests
import time

ray.init(num_cpus=4)
client = serve.start()
sinkEndpointRoute = "/toslack"


# Option 1: Use existing API.
data = "First attempt: this is the body of the request!"

client.create_backend("kamel_slack_backend", kamel_backend.KamelSinkHandler)
client.create_endpoint("output_to_slack", backend="kamel_slack_backend", route=sinkEndpointRoute, methods=["POST"])

externalEvent = kamel_backend.ExternalEvent(sinkEndpointRoute, data)

# Using HTTP requests directly.
# answerAsStr = requests.post("http://127.0.0.1:8000/toslack", data="First attempt: this is the body of the request!").text

# Using Ray's endpoint API:
answerAsStr = ray.get(client.get_handle("output_to_slack").remote(externalEvent))
print(answerAsStr)

client.delete_endpoint("output_to_slack")
client.delete_backend("kamel_slack_backend")


# Option 2: Use new API which allows usage of proxy endpoints.
data = "Second attempt: this is the body of the request!"

# client.create_backend("kamel_slack_backend", kamel_backend.KamelSinkHandler)
sinkBackend = kamel_backend.KamelBackend(client)

# client.create_external_endpoint("output_to_slack", backend="kamel_slack_backend", route=sinkEndpointRoute, methods=["POST"])
sinkBackend.createProxyEndpoint("output_to_slack", sinkEndpointRoute)

answerAsStr = ""
for i in range(10):
    answerAsStr = sinkBackend.postToProxyEndpoint("output_to_slack", data + " Order number: %s" % i)
print(answerAsStr)

sinkBackend.removeProxyEndpoint("output_to_slack")


# Option 3: no backend, just topics
data = "Third attempt: this is the body of the request!"

# Create topic.
sinkTopic = topics.EventTopic.remote("slackSinkTopic")

# Create actor subscriber.
slackSinkActor = kamel_backend.SinkSubscriber.remote(sinkEndpointRoute)

# Subscribe method for sending data to sink.
sinkTopic.subscribe.remote(slackSinkActor.sendToSink)

# Publish with argument.
sinkTopic.publishToRemote.remote(data)

# Does not work as expected. Sending repeated requests required a queue which
# a plain actor does not have.
# for i in range(10):
#     # Since no queues are in place use the timer to stagger requests.
#     time.sleep(1)
#     sinkTopic.publishToRemote.remote(data + " Order number: %s" % i)
