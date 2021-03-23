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

from rayvens.core.camel_anywhere import kamel_utils
from rayvens.core.camel_anywhere.mode import mode
import os

# Method to install kamel in a cluster.
# The cluster needs to be already started. An operator image, and a registry
# that Camel-K can use to publish newly created images to are needed.


def install(kamelImage,
            publishRegistry,
            mode=mode,
            localCluster=False,
            usingKind=False,
            insecureRegistry=False):
    # Enforce local cluster, for now.
    # TODO: make this work in an actual cluster.
    if not localCluster:
        raise RuntimeError('only local clusters are supported')

    # If running a local cluster (i.e. cluster running on local machine)
    # then only the kind cluster is supported.
    # TODO: enable this for other cluster types.
    if localCluster and not usingKind:
        raise RuntimeError('locally, only kind cluster is supported')

    command = ["install"]

    # Namespace
    command.append("-n")
    command.append(mode.getNamespace())

    # Add kamel operator image.
    command.append("--operator-image")
    command.append(kamelImage)

    # Add registry that kamel can use for image publication.
    command.append("--registry")

    # Kind cluster starts with a registry.
    if usingKind:
        command.append(publishRegistry)

    # Local registry used to publish newly constructed images is insecure.
    # TODO: support secure registries.
    if (insecureRegistry):
        command.append("--registry-insecure")

    # Force installation.
    command.append("--force")

    return kamel_utils.invokeReturningCmd(command, mode, "camel-k-operator")


# Invoke kamel uninstall.


def uninstall(installInvocation):
    command = ["uninstall"]

    # Namespace
    command.append("-n")
    command.append(mode.getNamespace())

    return kamel_utils.invokeReturningCmd(command, installInvocation.getMode(),
                                          "camel-k-operator")


# Kamel run invocation.


def run(integration_files,
        mode,
        integration_name,
        local=None,
        envVars=[],
        integration_as_files=True,
        await_start=False,
        inverted_http=False):
    # Use the mode to determine if this is a local run or a run.
    isLocal = mode.isLocal()

    # If the local argument is other than None use it to overwrite the
    # mode.
    if local is not None:
        isLocal = local

    # Invoke either kamel local run or kamel run.
    if not isLocal:
        command = ["run"]

        # Integration name.
        command.append("--name")
        command.append(integration_name)

        # Namespace
        command.append("-n")
        command.append(mode.getNamespace())

        for envVar in envVars:
            if envVar not in os.environ:
                raise RuntimeError(
                    "Variable %s not set in current environment" % envVar)
            command.append("--env")
            command.append("%s=%s" % (envVar, os.getenv(envVar)))
    else:
        command = ["local", "run"]

    # If files were provided then incorporate them inside the command.
    # Otherwise send the integration file content list to the invocation actor.
    integration_content = []
    if integration_as_files:
        command.append(" ".join(integration_files))
    else:
        integration_content = integration_files

    # If this is a kamel local run, the behavior of the command is slightly
    # different and needs to be handled separately.
    if isLocal:
        return kamel_utils.invokeLocalOngoingCmd(
            command,
            mode,
            integration_name,
            integration_content=integration_content,
            inverted_http=inverted_http)

    return kamel_utils.invokeReturningCmd(
        command,
        mode,
        integration_name,
        integration_content=integration_content,
        await_start=await_start,
        inverted_http=inverted_http)


# Kamel delete invocation.


def delete(runningIntegrationInvocation, integration_name):
    # Compose command with integration name.
    command = ["delete"]

    # Namespace
    command.append("-n")
    command.append(runningIntegrationInvocation.getNamespace())

    command.append(integration_name)

    return kamel_utils.invokeReturningCmd(
        command, runningIntegrationInvocation.getMode(), integration_name)
