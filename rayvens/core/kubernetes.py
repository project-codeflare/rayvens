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

import os
from rayvens.core import utils
from rayvens.core import kubernetes_utils

# Port used by the Quarkus Runtime to listen to HTTP requests.
quarkus_listener_port = "8080"

# Wait for pod to reach running state.


def pod_running_status(mode, integration_name):
    # TODO: adapt this to support multiple namespaces.
    command = ["get", "pods", "-w"]

    # Namespace
    command.append("-n")
    command.append(mode.namespace)

    return kubernetes_utils.pod_status(command, integration_name)


# Wait for integration to reach running state.


def integration_status(mode, pod_name, message=None):
    # TODO: adapt this to support multiple namespaces.
    command = ["logs", pod_name]

    # Namespace
    command.append("-n")
    command.append(mode.namespace)

    # Stream output from this command.
    command.append("--follow=true")

    return kubernetes_utils.invoke_kubectl_command(command,
                                                   message=message,
                                                   ongoing=True)


# Create service that Ray can talk to from outside the cluster.


def create_kamel_external_service(mode, service_name, integration_name):
    # Compose yaml file.
    yaml_file = f"""
kind: Service
apiVersion: v1
metadata:
  name: {service_name}
spec:
  ports:
  - nodePort: {utils.externalized_cluster_port}
    port: {quarkus_listener_port}
    protocol: TCP
    targetPort: {quarkus_listener_port}
  selector:
    camel.apache.org/integration: {integration_name}
  type: NodePort
    """

    # Write to output yaml file.
    output_file_name = os.path.abspath(service_name + ".yaml")
    output_file = open(output_file_name, "w")
    output_file.write(yaml_file)
    output_file.close()

    # Start service and check that it has started.
    service_started = False
    command = ["apply", "-f", output_file_name]

    # Namespace
    command.append("-n")
    command.append(mode.namespace)

    if kubernetes_utils.invoke_kubectl_command(command,
                                               service_name=service_name):
        command = ["get", "services", "-w"]

        # Namespace
        command.append("-n")
        command.append(mode.namespace)

        service_started = kubernetes_utils.invoke_kubectl_command(
            command, service_name=service_name, ongoing=True)

    if service_started:
        print("Service %s has been started successfully." % service_name)

    # Remove intermediate file.
    if output_file_name is not None:
        os.remove(output_file_name)


# Delete service.


def delete_service(mode, service_name):
    command = ["delete", "service", service_name]

    # Namespace
    command.append("-n")
    command.append(mode.namespace)

    return kubernetes_utils.invoke_kubectl_command(command,
                                                   service_name=service_name)
