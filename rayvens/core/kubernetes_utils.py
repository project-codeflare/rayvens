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

from enum import Enum
from rayvens.core import invocation


class KubectlCommand(Enum):
    GET_PODS = 1
    GET_SERVICES = 2
    GET_DEPLOYMENTS = 3
    APPLY = 4
    DELETE_SERVICE = 5
    LOGS = 6


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
    if command.startswith("logs"):
        return KubectlCommand.LOGS
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
    if commandType == KubectlCommand.LOGS:
        return "logs"
    raise RuntimeError('unsupported kubectl subcommand')


def getKubectlCommandEndCondition(subcommandType, serviceName):
    if subcommandType == KubectlCommand.GET_PODS:
        return ""
    if subcommandType == KubectlCommand.GET_SERVICES:
        return ""
    if subcommandType == KubectlCommand.GET_DEPLOYMENTS:
        return ""
    if subcommandType == KubectlCommand.APPLY:
        if serviceName is None or serviceName == "":
            raise RuntimeError("Invalid kubernetes service name.")
        return "%s created" % serviceName
    if subcommandType == KubectlCommand.DELETE_SERVICE:
        if serviceName is None or serviceName == "":
            raise RuntimeError("Invalid kubernetes service name.")
        return "service \"%s\" deleted" % serviceName
    if subcommandType == KubectlCommand.LOGS:
        return "Installed features:"
    raise RuntimeError('unsupported kubectl subcommand: %s' %
                       getKubectlCommandString(subcommandType))


def extractPodFullName(line, podBaseName):
    # Check if line contins pod name.
    if podBaseName not in line:
        return ""

    # Split line into tokens.
    wordList = line.split()
    # If line is too short to be a valid pod line then exit.
    if len(wordList) < 1:
        return ""

    return wordList[0]


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
    if len(wordList) < 2:
        return False

    if wordList[0] == fullPodName:
        for state in stateList:
            if state == wordList[2]:
                return True
    return False


def isInRunningState(line, fullPodName):
    return isInState(line, fullPodName, ["Running"])


def isInErrorState(line, fullPodName):
    return isInState(line, fullPodName, ["Error", "CrashLoopBackOff"])


# Helper for invoking a long running kubectl command.
def getPodStatusCmd(command, integrationName):
    # Invoke command using the Kubectl invocation actor.
    kubectlInvocation = invocation.KubectlInvocation(command)

    # Wait for kubectl command to finish checking the integration.
    podIsRunning = kubectlInvocation.podIsInRunningState(integrationName)
    podName = kubectlInvocation.getPodFullName()

    # Stop kubectl command.
    kubectlInvocation.kill()

    # Return pod status
    return podIsRunning, podName


# Helper for starting a service. Command returns immediately.
def executeReturningKubectlCmd(command, service_name=None, with_output=False):
    # Invoke command using the Kubectl invocation actor.
    kubectl_invocation = invocation.KubectlInvocation(command, service_name)

    # Wait for kubectl command to return.
    outcome = kubectl_invocation.executeKubectlCmd(service_name, with_output)

    # Return outcome.
    return outcome


# Helper for check that a service exists.
def executeOngoingKubectlCmd(command,
                             message,
                             service_name=None,
                             with_output=False):
    # Invoke command using the Kubectl invocation actor.
    kubectl_invocation = invocation.KubectlInvocation(command, service_name)

    # Wait for kamel command to finish launching the integration.
    outcome = kubectl_invocation.executeKubectlCmd(message, service_name,
                                                   with_output)

    # Stop kubectl command.
    kubectl_invocation.kill()

    # Return service status
    return outcome
