import ray
import subprocess
import os
import signal
import sys
import io
from events import utils
from events import kamel_utils
from events import kubernetes_utils

#
# Wrap invocation as actor. This is an invocation for kamel local run.
#
@ray.remote
class KamelInvocationActor:
    subprocessName = "Kamel"

    def __init__(self, commandOptions, baseName=""):
        # If list is porvided, join it.
        if isinstance(commandOptions, list):
            commandOptions = " ".join(commandOptions)

        # Get subcommand type.
        self.subcommandType = kamel_utils.getKamelCommandType(commandOptions)

        # Create the kamel command.
        execCommand = " ".join(["exec", "kamel", commandOptions])

        # Fail early before command is invoked if kamel is not found.
        if not utils.executableIsAvailable("kamel"):
            raise RuntimeError('kamel executable not found in PATH')

        # Fail if this is not a local command and kubectl is not found.
        if not kamel_utils.isLocalCommand(self.subcommandType) and \
           not utils.executableIsAvailable("kubectl"):
            raise RuntimeError('kubectl executable not found in PATH for non-local kamel command')

        # Get end condition or fail if command type is not supported.
        self.endCondition = kamel_utils.getKamelCommandEndCondition(self.subcommandType, baseName)

        # TODO: Does this work for Windows? Linux? Cloud?
        # Launch kamel command in a new process.
        self.process = subprocess.Popen(execCommand,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            preexec_fn=os.setsid)

    def isLocalOngoingKamelReady(self):
        # Check if kamel instance launched correctly.
        instantiationFailed = False
        while True:
            # Log progress of kamel subprocess.
            # TODO: better logging. Merge logs?
            # TODO: We only show logs for start-up, can we show logs during runtime?
            output = utils.printLogFromSubProcess(self.subprocessName, self.process)

            returnCode = self.process.poll()
            if returnCode is not None:
                instantiationFailed = True
                break
            # Some form of completion signal is received.
            # Use the Kamel output to decide when Kamel instance is
            # ready to receive requests.
            # TODO: brittle, check process completion by checking if it has started
            # listening on the host:port.
            if self.endCondition in output:
                break

        # Emit success/fail message.
        logMessage = "Kamel integration is ready."
        if instantiationFailed:
            logMessage = "Kamel integration failed to start."

        utils.printLog(self.subprocessName, logMessage)

        return not instantiationFailed

    def isReturningKamelReady(self):
        success = False
        for line in io.TextIOWrapper(self.process.stdout, encoding="utf-8"):
            line = line.strip()
            # Only output non-emoty lines.
            if line != "":
                utils.printLog(self.subprocessName, line)
            if self.endCondition in line:
                success = True

        # Log outcome.
        subcommand = kamel_utils.getKamelCommandString(self.subcommandType)
        logMessage = "Kamel `%s` command finished successfully." % subcommand
        if not success:
            logMessage = "Kamel `%s` command failed."  % subcommand
        utils.printLog(self.subprocessName, logMessage)
        return success

    def getSubcommandType(self):
        return self.subcommandType

    def kill(self):
        # Magic formula for terminating all processes in the group including
        # any subprocesses that the kamel command might have created.
        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

#
# Handle calls to Kubernetes kubectl.
#
@ray.remote
class KubectlInvocationActor:
    subprocessName = "Kubectl"

    def __init__(self, commandOptions, k8sName=""):
        # If list is porvided, join it.
        if isinstance(commandOptions, list):
            commandOptions = " ".join(commandOptions)

        # Initialize state.
        self.subcommandType = kubernetes_utils.getKubectlCommandType(commandOptions)
        self.isRunning = False
        # TODO: rename this, this can be either a pod or a service or a deployment name.
        self.podName = ""

        # Get end condition or fail if command type is not supported.
        self.endCondition = kubernetes_utils.getKubectlCommandEndCondition(self.subcommandType, k8sName)

        # Create the kubectl command.
        execCommand = " ".join(["exec", "kubectl", commandOptions])

        # Launch kamel command in a new process.
        self.process = subprocess.Popen(execCommand,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            preexec_fn=os.setsid)

    def executeKubectlCmd(self, serviceName):
        success = False
        while True:
            output = utils.printLogFromSubProcess(self.subprocessName, self.process)
            if self.subcommandType == kubernetes_utils.KubectlCommand.GET_SERVICES:
                if kubernetes_utils.serviceNameMatches(output, serviceName):
                    success = True
                    break
            elif self.endCondition in output:
                success = True
                break

            returnCode = self.process.poll()
            if returnCode is not None:
                break

        subcommand = kubernetes_utils.getKubectlCommandString(self.subcommandType)
        logMessage = "Kubectl %s command finished successfully." % subcommand
        if not success:
            logMessage = "Kubectl %s command failed." % subcommand
        utils.printLog(self.subprocessName, logMessage)

        return success

    def podIsInRunningState(self, integrationName):
        while True:
            # Process output line by line until we find the pod we are looking for.
            # There should only be one new pod.
            output = utils.printLogFromSubProcess(self.subprocessName, self.process)
            if self.podName == "":
                self.podName = kubernetes_utils.extractPodFullName(output, integrationName)

            if kubernetes_utils.isInRunningState(output, self.podName):
                self.isRunning = True
                break

            if kubernetes_utils.isInErrorState(output, self.podName):
               break

            # Return if command has exited.
            returnCode = self.process.poll()
            if returnCode is not None:
                break

        logMessage = "Pod with name `%s` is now Running." % self.podName
        if not self.isRunning:
            logMessage = "Pod with name `%s` failed to start."  % self.podName
        utils.printLog(self.subprocessName, logMessage)

        return self.isRunning

    def getPodFullName(self):
        return self.podName

    def kill(self):
        # Terminating all processes in the group including any subprocesses
        # that the kubectl command might have created.
        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
