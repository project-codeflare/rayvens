import ray
from misc.events import utils
import requests

# Default value for Quarkus HTTP server.
# TODO: multiple sinks will require multiple ports.
quarkusHTTPServerLocal = "http://0.0.0.0:8080"
quarkusHTTPServerLocalCluster = "http://localhost:%s" % \
    utils.externalizedClusterPort

# Can we create a Ray backend which has an external endpoint that has a handle
# in Ray?
# i.e. have a proxy endpoint that Ray code can use and will forward traffic to
# the external endpoint which is not managed by Ray.


class ExternalEvent:
    def __init__(self, route, data):
        self.route = route
        self.data = data

    def getRoute(self):
        return self.route

    def getData(self):
        return self.data


class KamelSinkHandler:
    def __init__(self, mode):
        self.mode = mode

    async def __call__(self, request):
        body = await request.body()
        if not isinstance(body, ExternalEvent):
            return {"message": "Failure"}

        endpoint = self.mode.getQuarkusHTTPServer() + body.getRoute()
        requests.post(endpoint, data=body.getData())
        return {"message": "Success"}


class KamelBackend:
    backendName = "kamel_backend"

    def __init__(self, client, mode):
        self.client = client
        # Create it as a normal backend.

        client.create_backend(self.backendName, KamelSinkHandler, mode)
        self.endpointToRoute = {}

    def createProxyEndpoint(self, endpointName, route):
        self.endpointToRoute[endpointName] = route

        # Create endpoint with method as POST.
        self.client.create_endpoint(endpointName,
                                    backend=self.backendName,
                                    route=route,
                                    methods=["POST"])

    def postToProxyEndpoint(self, endpointName, data):
        # Retrieve route.
        route = self.endpointToRoute[endpointName]

        # Internal data format.
        externalEvent = ExternalEvent(route, data)

        # Send request to backend.
        answerAsStr = ray.get(
            self.client.get_handle(endpointName).remote(externalEvent))

        return answerAsStr

    def removeProxyEndpoint(self, endpointName):
        self.client.delete_endpoint(endpointName)
        self.endpointToRoute.pop(endpointName)


# Method which send post request to external Camel-K sink.


@ray.remote
class SinkSubscriber(object):
    def __init__(self, route):
        self.route = route

    def sendToSink(self, data):
        requests.post(quarkusHTTPServerLocal + self.route, data=data)
