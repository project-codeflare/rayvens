# Port externalized by the cluster.
# TODO: randomize this port as part of the supported list of ports.
externalizedClusterPort = "31093"

# Port used by the Quarkus Runtime to listen to HTTP requests.
# TODO: this value is just the default and can be customized in case
# several services are listening to events.
quarkusListenerPort = "8080"

# Port for internal communication inside the cluster.
# TODO: randomize this port as part of the supported list of ports.
internalClusterPort = "80"

# Check if the executable exists in PATH. This method should work
# in Windows, Linux and MacOS. Python >= 3.3 required.


def executableIsAvailable(executableName):
    from shutil import which
    return which(executableName) is not None


def subprocessTag(subprocessName):
    return "[%s subprocess]" % subprocessName


def printLogFromSubProcess(subprocessName, process):
    output = process.stdout.readline().decode("utf-8")
    output = output.strip()

    if output != "":
        print(subprocessTag(subprocessName), output)

    return output


def printLog(subprocessName, message):
    print(subprocessTag(subprocessName), message)
