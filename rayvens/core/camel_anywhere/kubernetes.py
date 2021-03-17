from rayvens.core.utils import utils
from rayvens.core.camel_anywhere import kubernetes_utils
import os

# Wait for pod to reach running state.


def getPodRunningStatus(mode, integration_name):
    # TODO: adapt this to support multiple namespaces.
    command = ["get", "pods", "-w"]

    # Namespace
    command.append("-n")
    command.append(mode.getNamespace())

    return kubernetes_utils.getPodStatusCmd(command, integration_name)


# Wait for integration to reach running state.


def getIntegrationStatus(mode, pod_name):
    # TODO: adapt this to support multiple namespaces.
    command = ["logs", pod_name]

    # Namespace
    command.append("-n")
    command.append(mode.getNamespace())

    # Stream output from this command.
    command.append("--follow=true")

    return kubernetes_utils.executeOngoingKubectlCmd(command)


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

    # Directory to output yaml file for the external connector.
    outputDirName = os.path.join(os.getcwd(), "kubernetes")

    # Check that the directory does not already exist.
    if not os.path.isfile(outputDirName) and not os.path.isdir(outputDirName):
        os.mkdir(outputDirName)

    # Write to output yaml file.
    outputFileName = os.path.join(outputDirName, serviceName + ".yaml")
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


# Delete service.


def deleteService(mode, serviceName):
    command = ["delete", "service", serviceName]

    # Namespace
    command.append("-n")
    command.append(mode.getNamespace())

    kubernetes_utils.executeReturningKubectlCmd(command, serviceName)
