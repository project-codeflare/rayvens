import ray
import requests

# Default value for Quarkus HTTP server.
# TODO: multiple sinks will require multiple ports.
quarkusHTTPServerLocal = "http://0.0.0.0:8080"

# Can we create a Ray backend which has an external endpoint that has a handle
# in Ray?
# i.e. have a proxy endpoint that Ray code can use and will forward traffic to
# the external endpoint which is not managed by Ray.


class ExternalEvent:
    def __init__(self, route, integration_name, source=False):
        self.route = route
        self.integration_name = integration_name
        self.data = None
        self.source = source

    def get_data(self):
        if self.data is None:
            raise RuntimeError(
                "Attempting to send event with None data field.")
        return self.data


class KamelEventHandler:
    def __init__(self, mode, topic):
        self.mode = mode
        self.topic = topic

    async def __call__(self, request):
        body = await request.body()
        if isinstance(body, ExternalEvent):
            endpoint = self.mode.getQuarkusHTTPServer(
                body.integration_name) + body.route
            requests.post(endpoint, data=body.get_data())
            return {"message": "Success"}

        if self.topic is None:
            return {"message": "Failure"}
        self.topic.append.remote(body)
        return {"message": "Success"}


class KamelBackend:
    backendName = "kamel_backend"

    def __init__(self, client, mode, topic=None, ray_actor_options={}):
        # Create it as a normal backend.
        client.create_backend(self.backendName,
                              KamelEventHandler,
                              mode,
                              topic,
                              config={'num_replicas': 1},
                              ray_actor_options=ray_actor_options)
        self.endpoint_to_event = {}

    def createProxyEndpoint(self, client, endpoint_name, route,
                            integration_name):
        self.endpoint_to_event[endpoint_name] = ExternalEvent(
            route, integration_name)
        print("Create: Length of endpoint_to_event list:",
              len(self.endpoint_to_event))

        # Create endpoint with method as POST.
        client.create_endpoint(endpoint_name,
                               backend=self.backendName,
                               route=route,
                               methods=["POST"])

    def _post_event(self, endpointHandle, endpoint_name, data):
        # Get partial event.
        print("Post: Length of endpoint_to_event list:",
              len(self.endpoint_to_event))
        event = self.endpoint_to_event[endpoint_name]

        # Populate data field.
        event.data = data

        # Send request to backend.
        return ray.get(endpointHandle.remote(event))

    def postToProxyEndpoint(self, client, endpoint_name, data):
        return self._post_event(client.get_handle(endpoint_name),
                                endpoint_name, data)

    def postToProxyEndpointHandle(self, endpointHandle, endpoint_name, data):
        return self._post_event(endpointHandle, endpoint_name, data)

    def removeProxyEndpoint(self, client, endpoint_name):
        client.delete_endpoint(endpoint_name)
        self.endpoint_to_event.pop(endpoint_name)


# Method which send post request to external Camel-K sink.


@ray.remote
class SinkSubscriber(object):
    def __init__(self, route):
        self.route = route

    def sendToSink(self, data):
        requests.post(quarkusHTTPServerLocal + self.route, data=data)
