from events import kubernetes_utils
from collections import namedtuple
from misc.events import utils
import os

# List that holds the list of active pods.
PodName = namedtuple('PodName', 'integrationName podName')
activePods = {}

# Wait for pod to reach running state.


def getPodRunningStatus(integrationName):
    # TODO: adapt this to support multiple namespaces.
    command = ["get", "pods", "-w", "--all-namespaces"]
    return kubernetes_utils.getPodStatusCmd(command, integrationName)


# Create service that Ray can talk to from outside the cluster.


def createExternalServiceForKamel(serviceName, integrationName):
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
    if kubernetes_utils.executeReturningKubectlCmd(command, serviceName):
        command = ["get", "services", "-w"]
        serviceHasBeenStarted = kubernetes_utils.executeOngoingKubectlCmd(
            command, serviceName)

    if serviceHasBeenStarted:
        print("Service %s has been started succesfully." % serviceName)


# Delete service.


def deleteService(serviceName):
    command = ["delete", "service", serviceName]
    kubernetes_utils.executeReturningKubectlCmd(command, serviceName)


def getInvocationFromIntegrationName(integrationName):
    for key in activePods:
        if getIntegrationName(key) == integrationName:
            return key
    return None


def getPodName(invocation):
    return activePods[invocation].podName


def getIntegrationName(invocation):
    return activePods[invocation].integrationName


def addActivePod(invocation, integrationName, podName):
    activePods[invocation] = PodName(integrationName, podName)


def deleteActivePod(invocation):
    del activePods[invocation]


def getNumActivePods():
    return len(activePods)
