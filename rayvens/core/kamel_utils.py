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
from rayvens.core import kubernetes


class KamelCommand(Enum):
    INSTALL = 1
    BUILD = 2
    RUN = 3
    LOCAL_BUILD = 4
    LOCAL_RUN = 5
    DELETE = 6
    UNINSTALL = 100


def getKamelCommandType(command):
    if command.startswith("install"):
        return KamelCommand.INSTALL
    if command.startswith("build"):
        return KamelCommand.BUILD
    if command.startswith("run"):
        return KamelCommand.RUN
    if command.startswith("local build"):
        return KamelCommand.LOCAL_BUILD
    if command.startswith("local run"):
        return KamelCommand.LOCAL_RUN
    if command.startswith("uninstall"):
        return KamelCommand.UNINSTALL
    if command.startswith("delete"):
        return KamelCommand.DELETE
    raise RuntimeError('unsupported kamel subcommand: %s' % command)


def getKamelCommandString(commandType):
    if commandType == KamelCommand.INSTALL:
        return "install"
    if commandType == KamelCommand.BUILD:
        return "build"
    if commandType == KamelCommand.RUN:
        return "run"
    if commandType == KamelCommand.LOCAL_BUILD:
        return "local build"
    if commandType == KamelCommand.LOCAL_RUN:
        return "local run"
    if commandType == KamelCommand.UNINSTALL:
        return "uninstall"
    if commandType == KamelCommand.DELETE:
        return "delete"
    raise RuntimeError('unsupported kamel subcommand')


def getKamelCommandEndCondition(subcommandType, baseName):
    if subcommandType == KamelCommand.INSTALL:
        return "Camel K installed in namespace"
    if subcommandType == KamelCommand.BUILD:
        return ""
    if subcommandType == KamelCommand.RUN:
        return ""
    if subcommandType == KamelCommand.LOCAL_BUILD:
        return ""
    if subcommandType == KamelCommand.LOCAL_RUN:
        return "Installed features:"
    if subcommandType == KamelCommand.UNINSTALL:
        return "Camel K Service Accounts removed from namespace"
    if subcommandType == KamelCommand.DELETE:
        return "Integration %s deleted" % baseName
    raise RuntimeError('unsupported kamel subcommand: %s' %
                       getKamelCommandString(subcommandType))


# Command types which are local.


def isLocalCommand(subcommandType):
    isLocal = subcommandType == KamelCommand.LOCAL_BUILD \
        or subcommandType == KamelCommand.LOCAL_RUN
    return isLocal


# Command types which lead to the creation of a kubectl service.


def createsKubectlService(subcommandType):
    return subcommandType == KamelCommand.INSTALL \
        or subcommandType == KamelCommand.RUN


# Command types which lead to the creation of a kubectl service.


def deletesKubectlService(subcommandType):
    return subcommandType == KamelCommand.DELETE \
        or subcommandType == KamelCommand.UNINSTALL


# Helper for ongoing local commands like kamel local run.


def invokeLocalOngoingCmd(command,
                          mode,
                          integration_name,
                          integration_content=[],
                          inverted_http=False):
    # Invoke command using the Kamel invocation actor.
    kamel_invocation = invocation.KamelInvocation(
        command,
        mode,
        integration_name=integration_name,
        integration_content=integration_content,
        inverted_http=inverted_http)

    # Wait for kamel command to finish launching the integration.
    kamel_is_ready = kamel_invocation.ongoing_command()

    # Log progress.
    print("kamel ongoing command is ready:", kamel_is_ready)

    # Invocation object is required later for stopping the integration.
    # TODO: find a better way to do invocation object management.
    if kamel_is_ready:
        return kamel_invocation

    return None


# Helper for returning kamel commands such as kamel install.


def invokeReturningCmd(command,
                       mode,
                       integration_name,
                       integration_content=[],
                       await_start=False,
                       inverted_http=False):
    kamel_invocation = invocation.KamelInvocation(
        command,
        mode,
        integration_name=integration_name,
        integration_content=integration_content,
        inverted_http=inverted_http)

    # Wait for the kamel command to be invoked and retrieve status.
    success = kamel_invocation.returning_command()

    # If command was no successful then exit early.
    if not success:
        return None

    if await_start:
        subcommandType = kamel_invocation.getSubcommandType()
        if createsKubectlService(subcommandType):
            # Ensure pod is running.
            pod_is_running, pod_name = kubernetes.getPodRunningStatus(
                mode, integration_name)
            if pod_is_running:
                print(f'Pod {pod_name} is running correctly.')
            else:
                print("Pod did not run correctly.")

            # Ensure integration is running.
            integration_is_running = kubernetes.getIntegrationStatus(
                mode, pod_name)
            if integration_is_running:
                print(f'Integration {integration_name} is running.')
            else:
                print('Integration did not start correctly.')

    return kamel_invocation