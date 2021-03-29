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

# Wait for pod to reach running state.


def getPodRunningStatus(mode, integration_name):
    # TODO: adapt this to support multiple namespaces.
    command = ["get", "pods", "-w"]

    # Namespace
    command.append("-n")
    command.append(mode.getNamespace())

    return kubernetes_utils.getPodStatusCmd(command, integration_name)


# Wait for integration to reach running state.


def getIntegrationStatus(mode, pod_name, message=None):
    # TODO: adapt this to support multiple namespaces.
    command = ["logs", pod_name]

    # Namespace
    command.append("-n")
    command.append(mode.getNamespace())

    # Stream output from this command.
    command.append("--follow=true")

    return kubernetes_utils.executeOngoingKubectlCmd(command, message)


# Create service that Ray can talk to from outside the cluster.


def createExternalServiceForKamel(mode, serviceName, integrationName):
    # Compose yaml file.
    yamlFile = """
kind: Service
apiVersion: v1
metadata:
  name: %s
spec:
  ports:
  - nodePort: %s
    port: %s
    protocol: TCP
    targetPort: %s
  selector:
    camel.apache.org/integration: %s
  type: NodePort
    """ % (serviceName, utils.externalizedClusterPort,
           utils.quarkusListenerPort, utils.quarkusListenerPort,
           integrationName)

    # Write to output yaml file.
    outputFileName = os.path.abspath(serviceName + ".yaml")
    outputFile = open(outputFileName, "w")
    outputFile.write(yamlFile)
    outputFile.close()

    # Start service and check that it has started.
    serviceHasBeenStarted = False
    command = ["apply", "-f", outputFileName]

    # Namespace
    command.append("-n")
    command.append(mode.getNamespace())

    if kubernetes_utils.executeReturningKubectlCmd(command, serviceName):
        command = ["get", "services", "-w"]

        # Namespace
        command.append("-n")
        command.append(mode.getNamespace())

        serviceHasBeenStarted = kubernetes_utils.executeOngoingKubectlCmd(
            command, serviceName)

    if serviceHasBeenStarted:
        print("Service %s has been started succesfully." % serviceName)

    # Remove intermediate file.
    if outputFileName is not None:
        os.remove(outputFileName)


# Delete service.


def deleteService(mode, serviceName):
    command = ["delete", "service", serviceName]

    # Namespace
    command.append("-n")
    command.append(mode.getNamespace())

    return kubernetes_utils.executeReturningKubectlCmd(command, serviceName)
