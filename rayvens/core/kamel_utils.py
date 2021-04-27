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


class KamelCommand(Enum):
    INSTALL = 1
    BUILD = 2
    RUN = 3
    LOCAL_BUILD = 4
    LOCAL_RUN = 5
    DELETE = 6
    LOG = 7
    UNINSTALL = 100


def kamel_command_type(command_options):
    command = ' '.join(command_options)
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
    if command.startswith("log"):
        return KamelCommand.LOG
    raise RuntimeError('unsupported kamel subcommand: %s' % command)


def kamel_command_str(command_type):
    if command_type == KamelCommand.INSTALL:
        return "install"
    if command_type == KamelCommand.BUILD:
        return "build"
    if command_type == KamelCommand.RUN:
        return "run"
    if command_type == KamelCommand.LOCAL_BUILD:
        return "local build"
    if command_type == KamelCommand.LOCAL_RUN:
        return "local run"
    if command_type == KamelCommand.UNINSTALL:
        return "uninstall"
    if command_type == KamelCommand.DELETE:
        return "delete"
    if command_type == KamelCommand.LOG:
        return "log"
    raise RuntimeError('unsupported kamel subcommand')


def kamel_command_end_condition(subcommand_type, base_name):
    if subcommand_type == KamelCommand.INSTALL:
        return "Camel K installed in namespace"
    if subcommand_type == KamelCommand.BUILD:
        return ""
    if subcommand_type == KamelCommand.RUN:
        return f"integration \"{base_name}\""
    if subcommand_type == KamelCommand.LOCAL_BUILD:
        return ""
    if subcommand_type == KamelCommand.LOCAL_RUN:
        return "Installed features:"
    if subcommand_type == KamelCommand.UNINSTALL:
        return "Camel K Service Accounts removed from namespace"
    if subcommand_type == KamelCommand.DELETE:
        return f"Integration {base_name} deleted"
    if subcommand_type == KamelCommand.LOG:
        return ""
    raise RuntimeError('unsupported kamel subcommand: %s' %
                       kamel_command_str(subcommand_type))


# Helper for ongoing local commands like kamel local run.


def invokeOngoingCmd(command,
                     mode,
                     integration_name,
                     integration_content=[],
                     message=None):
    # Invoke command using the Kamel invocation actor.
    kamel_invocation = invocation.KamelInvocation(
        command,
        mode,
        integration_name=integration_name,
        integration_content=integration_content)

    # Wait for kamel command to finish launching the integration.
    kamel_is_ready = kamel_invocation.ongoing_command(message)

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
                       integration_content=[]):
    kamel_invocation = invocation.KamelInvocation(
        command,
        mode,
        integration_name=integration_name,
        integration_content=integration_content)

    # Wait for the kamel command to be invoked and retrieve status.
    success = kamel_invocation.returning_command()

    # If command was no successful then exit early.
    if not success:
        return None

    return kamel_invocation
