import ray
import events.utils
from enum import Enum
from events import invocation

# List that holds the list of active pods.
activePods = []

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

def getKubectlCommandEndCondition(subcommandType):
    if subcommandType == KubectlCommand.GET_PODS:
        return "Running"
    else:
        raise RuntimeError('unsupported kubectl subcommand: %s' % getKubectlCommandString(subcommandType))

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
