import ray
from rayvens.core.camel_anywhere import kamel_utils
from rayvens.core.camel_anywhere import kubernetes
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

    return kamel_utils.invokeReturningCmd(
        command, ray.get(installInvocation.getMode.remote()),
        "camel-k-operator")


# Kamel run invocation.


def run(integration_files,
        mode,
        integration_name,
        envVars=[],
        integration_as_files=True):
    command = ["run"]

    # Integration name.
    command.append("--name")
    command.append(integration_name)

    # Namespace
    command.append("-n")
    command.append(mode.getNamespace())

    for envVar in envVars:
        if envVar not in os.environ:
            raise RuntimeError("Variable %s not set in current environment" %
                               envVar)
        command.append("--env")
        command.append("%s=%s" % (envVar, os.getenv('SLACK_WEBHOOK')))

    # If files were provided then incorporate them inside the command.
    # Otherwise send the integration file content list to the invocation actor.
    integration_content = []
    if integration_as_files:
        command.append(" ".join(integration_files))
    else:
        integration_content = integration_files

    return kamel_utils.invokeReturningCmd(command, mode, integration_name,
                                          integration_content)


# Kamel delete invocation.


def delete(runningIntegrationInvocation):
    # Fetch integration name.
    integrationName = kubernetes.getIntegrationName(
        runningIntegrationInvocation)

    # Compose command with integration name.
    command = ["delete"]

    # Namespace
    command.append("-n")
    command.append(ray.get(runningIntegrationInvocation.getNamespace.remote()))

    command.append(integrationName)

    return kamel_utils.invokeReturningCmd(
        command, ray.get(runningIntegrationInvocation.getMode.remote()),
        integrationName)


# Invoke kamel local run on a given list of integration files.
# TODO: Explore merging topics and invocation actors. Listen on a topic and
# attach an external source/sink to it.


def localRun(integrationFiles):
    command = ["local", "run", " ".join(integrationFiles)]
    return kamel_utils.invokeLocalOngoingCmd(command)
