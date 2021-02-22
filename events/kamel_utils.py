import ray
import events.utils
from enum import Enum
from events import invocation

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

def isLocalCommand(subcommandType):
    isLocal = subcommandType == KamelCommand.LOCAL_BUILD \
        or subcommandType == KamelCommand.LOCAL_RUN
    return isLocal

# Helper for ongoing local commands like kamel local run.
def invokeLocalOngoingCmd(command):
    # Invoke command using the Kamel invocation actor.
    kamelInvocation = invocation.KamelInvocationActor.remote(" ".join(command))

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
    kamelInvocation = invocation.KamelInvocationActor.remote(" ".join(command))

    # Wait for kamel command to finish launching the integration.
    success = ray.get(kamelInvocation.isReturningKamelReady.remote())
