import ray
import events.utils
from enum import Enum
from events import invocation
from events import kubernetes

class KamelCommand(Enum):
    INSTALL     = 1
    BUILD       = 2
    RUN         = 3
    LOCAL_BUILD = 4
    LOCAL_RUN   = 5
    UNINSTALL   = 100

def getKamelCommandType(command):
    if command.startswith("install"):
        return KamelCommand.INSTALL
    elif command.startswith("build"):
        return KamelCommand.BUILD
    elif command.startswith("run"):
        return KamelCommand.RUN
    elif command.startswith("local build"):
        return KamelCommand.LOCAL_BUILD
    elif command.startswith("local run"):
        return KamelCommand.LOCAL_RUN
    elif command.startswith("uninstall"):
        return KamelCommand.UNINSTALL
    else:
        raise RuntimeError('unsupported kamel subcommand: %s' % command)

def getKamelCommandString(commandType):
    if commandType == KamelCommand.INSTALL:
        return "install"
    elif commandType == KamelCommand.BUILD:
        return "build"
    elif commandType == KamelCommand.RUN:
        return "run"
    elif commandType == KamelCommand.LOCAL_BUILD:
        return "local build"
    elif commandType == KamelCommand.LOCAL_RUN:
        return "local run"
    elif commandType == KamelCommand.UNINSTALL:
        return "uninstall"
    else:
        raise RuntimeError('unsupported kamel subcommand')

def getKamelCommandEndCondition(subcommandType):
    if subcommandType == KamelCommand.INSTALL:
        return "Camel K installed in namespace"
    elif subcommandType == KamelCommand.BUILD:
        return ""
    elif subcommandType == KamelCommand.RUN:
        return ""
    elif subcommandType == KamelCommand.LOCAL_BUILD:
        return ""
    elif subcommandType == KamelCommand.LOCAL_RUN:
        return "Installed features:"
    elif subcommandType == KamelCommand.UNINSTALL:
        return "Camel K Service Accounts removed from namespace"
    else:
        raise RuntimeError('unsupported kamel subcommand: %s' % getKamelCommandString(subcommandType))

# Command types which are local.
def isLocalCommand(subcommandType):
    isLocal = subcommandType == KamelCommand.LOCAL_BUILD \
        or subcommandType == KamelCommand.LOCAL_RUN
    return isLocal

# Command types which lead to the creation of a kubectl service.
def createsKubectlService(subcommandType):
    # TODO: extend this to include kamel run, for now only kamel install is supported.
    # createsService = subcommandType == KamelCommand.INSTALL \
    #     or subcommandType == KamelCommand.RUN
    createsService = subcommandType == KamelCommand.INSTALL
    return createsService

# Helper for ongoing local commands like kamel local run.
def invokeLocalOngoingCmd(command):
    # Invoke command using the Kamel invocation actor.
    kamelInvocation = invocation.KamelInvocationActor.remote()

    # Wait for kamel command to finish launching the integration.
    kamelIsReady = ray.get(kamelInvocation.isLocalOngoingKamelReady.remote())

    # Log progress.
    print("kamel ongoing command is ready:", kamelIsReady)

    # Invocation object is required later for stopping the integration.
    # TODO: find a better way to do invocation object management.
    return kamelInvocation

# Helper for non-local ongoing commands like kamel run.
# TODO: kubectl must be used to interact with the output of the process.
# TODO: implement this method.
def invokeOngoingCmd(command):
    pass

# Helper for returning kamel commands such as kamel install.
def invokeReturningCmd(command):
    kamelInvocation = invocation.KamelInvocationActor.remote(command)

    # Wait for the kamel command to be invoked and retrieve status.
    success = ray.get(kamelInvocation.isReturningKamelReady.remote())

    # If the command starts a service then check when the command has
    # reached running state.
    subcommandType = ray.get(kamelInvocation.getSubcommandType.remote())
    if createsKubectlService(subcommandType):
        # When pod is in running state add it to the list of existing pods.
        # TODO: for kamel run, the pod base name is the name of the file
        podIsRunning, fullPodName = kubernetes.getPodRunningStatus("camel-k-operator")
        if podIsRunning:
            print("Pod is running correctly. The full name of the pod is:", fullPodName)
        else:
            print("Pod did not run correctly.")
