import ray
from enum import Enum
from rayvens.core.camel_anywhere import invocation
from rayvens.core.camel_anywhere import kubernetes


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
    createsService = subcommandType == KamelCommand.INSTALL \
        or subcommandType == KamelCommand.RUN
    return createsService


# Command types which lead to the creation of a kubectl service.


def deletesKubectlService(subcommandType):
    return subcommandType == KamelCommand.DELETE


def isUinstallCommand(subcommandType):
    return subcommandType == KamelCommand.UNINSTALL


# Helper for ongoing local commands like kamel local run.


def invokeLocalOngoingCmd(command, mode):
    # Invoke command using the Kamel invocation actor.
    kamelInvocation = invocation.KamelInvocationActor.remote(command, mode)

    # Wait for kamel command to finish launching the integration.
    kamelIsReady = ray.get(kamelInvocation.isLocalOngoingKamelReady.remote())

    # Log progress.
    print("kamel ongoing command is ready:", kamelIsReady)

    # Invocation object is required later for stopping the integration.
    # TODO: find a better way to do invocation object management.
    if kamelIsReady:
        return kamelInvocation

    return None


# Helper for non-local ongoing commands like kamel run.
# TODO: kubectl must be used to interact with the output of the process.
# TODO: implement this method.


def invokeOngoingCmd(command):
    pass


# Helper for returning kamel commands such as kamel install.


def invokeReturningCmd(command,
                       mode,
                       integration_name,
                       integration_content=[]):
    kamelInvocation = invocation.KamelInvocationActor.remote(
        command, mode, integration_name, integration_content)

    # Wait for the kamel command to be invoked and retrieve status.
    success = ray.get(kamelInvocation.isReturningKamelReady.remote())

    # If command was no successful then exit early.
    if not success:
        return None

    # If the command starts a service then check when the command has
    # reached running state.
    subcommandType = ray.get(kamelInvocation.getSubcommandType.remote())
    if createsKubectlService(subcommandType):
        # When pod is in running state add it to the list of existing pods.
        podIsRunning, podName = kubernetes.getPodRunningStatus(
            integration_name)
        if podIsRunning:
            print("Pod is running correctly. The full name of the pod is:",
                  podName)
            kubernetes.addActivePod(kamelInvocation, integration_name, podName)
        else:
            print("Pod did not run correctly.")

    if deletesKubectlService(subcommandType):
        kubernetes.deleteActivePod(
            kubernetes.getInvocationFromIntegrationName(integration_name))

    if isUinstallCommand(subcommandType):
        kubernetes.deleteActivePod(
            kubernetes.getInvocationFromIntegrationName(integration_name))

    return kamelInvocation
