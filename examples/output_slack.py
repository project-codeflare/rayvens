import ray
from events import kamel_backend
from events import topics
from ray import serve
import requests

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

sinkBackend = kamel_backend.KamelBackend(client)

sinkBackend.createProxyEndpoint("output_to_slack", sinkEndpointRoute)

answerAsStr = sinkBackend.postToProxyEndpoint("output_to_slack", data)
print(answerAsStr)

sinkBackend.removeProxyEndpoint("output_to_slack")
