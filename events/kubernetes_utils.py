import ray
import events.utils
from enum import Enum
from events import invocation

# List that holds the list of active pods.
activePods = {}

class KubectlCommand(Enum):
    GET_PODS     = 1

def getKubectlCommandType(command):
    if command.startswith("get pods"):
        return KubectlCommand.GET_PODS
    else:
        raise RuntimeError('unsupported kubectl subcommand: %s' % command)

def getKubectlCommandString(commandType):
    if commandType == KubectlCommand.GET_PODS:
        return "get pods"
    else:
        raise RuntimeError('unsupported kubectl subcommand')

def extractPodFullName(line, podBaseName, existingPods):
    # Check if line contins pod name.
    if not podBaseName in line:
        return ""

    # Split line into tokens.
    wordList = line.split()
    # If line is too short to be a valid pod line then exit.
    if len(wordList) < 2:
        return ""

    # Check pod is not one of the existing ones.
    for pod in existingPods:
        if pod == wordList[1]:
            return ""

    return wordList[1]

def isInState(line, fullPodName, stateList):
    if fullPodName == "" or line == "":
        return False

    # Split line into tokens.
    wordList = line.split()
    # If line is too short to be a valid pod line then exit.
    if len(wordList) < 4:
        return False

    if wordList[1] == fullPodName:
        for state in stateList:
            if state == wordList[3]:
                return True
    return False

def isInRunningState(line, fullPodName):
    return isInState(line, fullPodName, ["Running"])

def isInErrorState(line, fullPodName):
    return isInState(line, fullPodName, ["Error", "CrashLoopBackOff"])

# Helper for invoking a long running kubectl command.
def getPodStatusCmd(command, podName):
    # Invoke command using the Kamel invocation actor.
    kubectlInvocation = invocation.KubectlInvocationActor.remote(command, activePods)

    # Wait for kamel command to finish launching the integration.
    podIsRunning = ray.get(kubectlInvocation.podIsInRunningState.remote(podName))
    podFullName = ray.get(kubectlInvocation.getPodFullName.remote())

    # TODO: add pod name to list of active pods

    # Stop kubectl command.
    kubectlInvocation.kill.remote()

    # Return pod status
    return podIsRunning, podFullName
