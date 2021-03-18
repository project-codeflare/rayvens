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
import requests

# Default value for Quarkus HTTP server.
# TODO: multiple sinks will require multiple ports.
quarkusHTTPServerLocal = "http://0.0.0.0:8080"

# Can we create a Ray backend which has an external endpoint that has a handle
# in Ray?
# i.e. have a proxy endpoint that Ray code can use and will forward traffic to
# the external endpoint which is not managed by Ray.


class SinkEvent:
    def __init__(self, route, integration_name):
        self.route = route
        self.integration_name = integration_name
        self.data = None

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
        if isinstance(body, SinkEvent):
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

    def __init__(self, client, mode, topic=None):
        # When the backend runs on a local machine we must allocate its
        # actor at least 1 CPU.
        actor_options = {'num_cpus': 0}
        if mode.isLocal() or mode.isMixed():
            actor_options = {'num_cpus': 1}
        client.create_backend(self.backendName,
                              KamelEventHandler,
                              mode,
                              topic,
                              config={'num_replicas': 1},
                              ray_actor_options=actor_options)
        self.endpoint_to_event = {}

    def createProxyEndpoint(self, client, endpoint_name, route,
                            integration_name):
        self.endpoint_to_event[endpoint_name] = SinkEvent(
            route, integration_name)

        # Create endpoint with method as POST.
        client.create_endpoint(endpoint_name,
                               backend=self.backendName,
                               route=route,
                               methods=["POST"])

    def _post_event(self, endpointHandle, endpoint_name, data):
        # Get partial event.s
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
