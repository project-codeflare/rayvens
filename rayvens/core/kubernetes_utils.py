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


def kubectl_command_type(command):
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


def kubectl_command_str(command_type):
    if command_type == KubectlCommand.GET_PODS:
        return "get pods"
    if command_type == KubectlCommand.GET_SERVICES:
        return "get services"
    if command_type == KubectlCommand.GET_DEPLOYMENTS:
        return "get deployments"
    if command_type == KubectlCommand.APPLY:
        return "apply"
    if command_type == KubectlCommand.DELETE_SERVICE:
        return "delete service"
    if command_type == KubectlCommand.LOGS:
        return "logs"
    raise RuntimeError('unsupported kubectl subcommand')


def kamel_command_end_condition(subcommand_type, service_name):
    if subcommand_type == KubectlCommand.GET_PODS:
        return ""
    if subcommand_type == KubectlCommand.GET_SERVICES:
        return ""
    if subcommand_type == KubectlCommand.GET_DEPLOYMENTS:
        return ""
    if subcommand_type == KubectlCommand.APPLY:
        if service_name is None or service_name == "":
            raise RuntimeError("Invalid kubernetes service name.")
        return "%s created" % service_name
    if subcommand_type == KubectlCommand.DELETE_SERVICE:
        if service_name is None or service_name == "":
            raise RuntimeError("Invalid kubernetes service name.")
        return "service \"%s\" deleted" % service_name
    if subcommand_type == KubectlCommand.LOGS:
        return "Installed features:"
    raise RuntimeError('unsupported kubectl subcommand: %s' %
                       kubectl_command_str(subcommand_type))


def extract_pod_name(line, pod_base_name):
    # Check if line contins pod name.
    if pod_base_name not in line:
        return ""

    # Split line into tokens.
    words = line.split()
    # If line is too short to be a valid pod line then exit.
    if len(words) < 1:
        return ""

    return words[0]


def service_name_matches(line, service_name):
    # Check if line contins pod name.
    if service_name not in line:
        return False

    # Split line into tokens.
    words = line.split()
    # If line is too short to be a valid pod line then exit.
    if len(words) < 1:
        return False

    return words[0] == service_name


def pod_state(line, pod_name, states):
    if pod_name == "" or line == "":
        return False

    # Split line into tokens.
    words = line.split()
    # If line is too short to be a valid pod line then exit.
    if len(words) < 2:
        return False

    if words[0] == pod_name:
        for state in states:
            if state == words[2]:
                return True
    return False


def is_pod_state_running(line, pod_name):
    return pod_state(line, pod_name, ["Running"])


def is_pod_state_error(line, pod_name):
    return pod_state(line, pod_name, ["Error", "CrashLoopBackOff"])


# Helper for checking pod status.
def pod_status(command, integration_name):
    # Invoke command using the Kubectl invocation class.
    kubectl_invocation = invocation.KubectlInvocation(command)

    # Wait for kubectl command to finish checking the integration.
    pod_running = kubectl_invocation.pod_is_running(integration_name)

    # Stop kubectl command.
    kubectl_invocation.kill()

    # Return pod status and full name.
    return pod_running, kubectl_invocation.pod_name


# Helper for running a kubectl command.
def invoke_kubectl_command(command,
                           message=None,
                           service_name=None,
                           with_output=False,
                           ongoing=False):
    # Invoke command using the Kubectl invocation class.
    kubectl_invocation = invocation.KubectlInvocation(command, service_name)

    # Wait for kubectl command to return.
    outcome = kubectl_invocation.invoke(message,
                                        service_name,
                                        with_output=with_output)

    # Stop kubectl ongoing command.
    if ongoing:
        kubectl_invocation.kill()

    # Return outcome.
    return outcome
