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
