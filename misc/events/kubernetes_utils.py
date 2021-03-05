import ray
from enum import Enum
from misc.events import invocation


class KubectlCommand(Enum):
    GET_PODS = 1
    GET_SERVICES = 2
    GET_DEPLOYMENTS = 3
    APPLY = 4
    DELETE_SERVICE = 5


def getKubectlCommandType(command):
    if command.startswith("get pods"):
        return KubectlCommand.GET_PODS
    if command.startswith("get services"):
        return KubectlCommand.GET_SERVICES
    if command.startswith("get deployments"):
        return KubectlCommand.GET_DEPLOYMENTS
    if command.startswith("apply"):
        return KubectlCommand.APPLY
    if command.startswith("delete service"):
        return KubectlCommand.DELETE_SERVICE
    raise RuntimeError('unsupported kubectl subcommand: %s' % command)


def getKubectlCommandString(commandType):
    if commandType == KubectlCommand.GET_PODS:
        return "get pods"
    if commandType == KubectlCommand.GET_SERVICES:
        return "get services"
    if commandType == KubectlCommand.GET_DEPLOYMENTS:
        return "get deployments"
    if commandType == KubectlCommand.APPLY:
        return "apply"
    if commandType == KubectlCommand.DELETE_SERVICE:
        return "delete service"
    raise RuntimeError('unsupported kubectl subcommand')


def getKubectlCommandEndCondition(subcommandType, serviceName):
    if subcommandType == KubectlCommand.GET_PODS:
        return ""
    if subcommandType == KubectlCommand.GET_SERVICES:
        return ""
    if subcommandType == KubectlCommand.GET_DEPLOYMENTS:
        return ""
    if subcommandType == KubectlCommand.APPLY:
        return "%s created" % serviceName
    if subcommandType == KubectlCommand.DELETE_SERVICE:
        return "service \"%s\" deleted" % serviceName
    raise RuntimeError('unsupported kubectl subcommand: %s' %
                       getKubectlCommandString(subcommandType))


def extractPodFullName(line, podBaseName):
    # Check if line contins pod name.
    if podBaseName not in line:
        return ""

    # Split line into tokens.
    wordList = line.split()
    # If line is too short to be a valid pod line then exit.
    if len(wordList) < 2:
        return ""

    return wordList[1]


def serviceNameMatches(line, serviceName):
    # Check if line contins pod name.
    if serviceName not in line:
        return False

    # Split line into tokens.
    wordList = line.split()
    # If line is too short to be a valid pod line then exit.
    if len(wordList) < 1:
        return False

    return wordList[0] == serviceName


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


def getPodStatusCmd(command, integrationName):
    # Invoke command using the Kubectl invocation actor.
    kubectlInvocation = invocation.KubectlInvocationActor.remote(command)

    # Wait for kubectl command to finish checking the integration.
    podIsRunning = ray.get(
        kubectlInvocation.podIsInRunningState.remote(integrationName))
    podName = ray.get(kubectlInvocation.getPodFullName.remote())

    # Stop kubectl command.
    kubectlInvocation.kill.remote()

    # Return pod status
    return podIsRunning, podName


# Helper for starting a service. Command returns immediately.


def executeReturningKubectlCmd(command, serviceName):
    # Invoke command using the Kubectl invocation actor.
    kubectlInvocation = invocation.KubectlInvocationActor.remote(
        command, serviceName)

    # Wait for kubectl command to return.
    outcome = ray.get(kubectlInvocation.executeKubectlCmd.remote(serviceName))

    # Return outcome.
    return outcome


# Helper for check that a service exists.


def executeOngoingKubectlCmd(command, serviceName):
    # Invoke command using the Kubectl invocation actor.
    kubectlInvocation = invocation.KubectlInvocationActor.remote(
        command, serviceName)

    # Wait for kamel command to finish launching the integration.
    outcome = ray.get(kubectlInvocation.executeKubectlCmd.remote(serviceName))

    # Stop kubectl command.
    kubectlInvocation.kill.remote()

    # Return service status
    return outcome
