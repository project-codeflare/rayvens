from events import kubernetes_utils
from collections import namedtuple

# List that holds the list of active pods.
PodName = namedtuple('PodName', 'integrationName podName')
activePods = {}

# Wait for pod to reach running state.
def getPodRunningStatus(integrationName):
    # TODO: adapt this to support multiple namespaces.
    command = ["get", "pods", "-w", "--all-namespaces"]
    return kubernetes_utils.getPodStatusCmd(command, integrationName)

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
