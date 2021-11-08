<!--
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
-->

# Rayvens CLI

Rayvens offers a command line interface for creating, launching and deleting integrations that receive or send events to external event sources and sinks respectively.

Requirements: Python 3.8+, Docker and Kubernetes.

## Integrations

Integrations are processes which interact with event sources and event sinks on behalf of the user. Integrations offer a uniform way to send/receive events between a user application and a diverse set of event sources and sinks.

The Rayvens CLI uses the `quay.io/rayvens` image registry to store intermediate images. Pre-built images exist of commonly used integrations such as `slack-sink`.

### Running a pre-built image locally:

To run the pre-built Slack sink integration run:

```
rayvens run --image quay.io/rayvens/slack-sink -p channel=<...> webhook_url=<...>
```

This will run the slack sink integration on the local machine as a Docker container. To view the created container perform a `docker ps`.

When the integration is ready to receive events, the command will output the endpoint on which it expects to receive events. For example:

```
> rayvens run --image quay.io/rayvens/slack-sink -p channel=<...> webhook_url=<...>
http://localhost:53844/my-integration-route
```

To remove the integration run:

```
rayvens delete --name slack-sink
```

This will stop, kill and remove the docker container from the list of existing containers.

### Removing an integration with a custom name:

By default the name of the integration being run is the integration type which is also the image name i.e. `slack-sink`. The name of the application can be set by the user using the `--name` flag:

```
rayvens run --image quay.io/rayvens/slack-sink -p channel=<...> webhook_url=<...> --name my-integration
```

Deleting this integration will now become:

```
rayvens delete --name my-integration
```

The command will delete all the docker containers with a name starting with the string `my-container`.

### Running a pre-built image in a Kubernetes cluster:
To run the pre-built Slack sink integration in a Kubernetes cluster add the `--deploy` flag to the previous command line:

```
rayvens run --image quay.io/rayvens/slack-sink -p channel=<...> webhook_url=<...> --deploy
```

To remove a Kubernetes-deployed integration with a default name run:

```
rayvens delete --name slack-sink --deployed
```

This command will remove any Kubernetes deployments and services.
