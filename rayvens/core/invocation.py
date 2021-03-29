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

import subprocess
import os
import signal
import io
import yaml
from rayvens.core import utils
from rayvens.core import kamel_utils
from rayvens.core import kubernetes_utils

#
# Wrap invocation as actor. This is an invocation for kamel local run.
#


class KamelInvocation:
    subprocess_name = "Kamel"

    def __init__(self,
                 command_options,
                 mode,
                 integration_name="",
                 integration_content=[],
                 inverted_http=False):
        self.mode = mode
        self.integration_name = integration_name

        if inverted_http:
            # Add Queue.java file.
            queue_file = os.path.join(os.path.dirname(__file__), 'Queue.java')
            command_options.append(queue_file)

            # TODO: Add random port for local run case.
            # self.port = utils.random_port()
            # command_options.append("--property")
            # command_options.append(f'quarkus.http.port={self.port}')

        # If list is porvided, join it.
        if isinstance(command_options, list):
            command_options = " ".join(command_options)

        # Create final kamel command.
        final_command = ["exec", "kamel", command_options]

        # If integration content is not null then we have files to create and
        # write to.
        # TODO: support multiple contents.
        self.filename = None
        for file_content in integration_content:
            self.filename = f'{self.integration_name}.yaml'
            with open(self.filename, 'w') as f:
                yaml.dump(file_content, f)
            self.filename = os.path.abspath(self.filename)
            final_command.append(self.filename)

        # Get subcommand type.
        self.subcommand_type = kamel_utils.getKamelCommandType(command_options)

        # Create the kamel command.
        exec_command = " ".join(final_command)

        print("Exec command => ", exec_command)
        # Add to PATH for case when this command is invoked in a cluster.
        if mode.isCluster():
            os.environ['PATH'] = ":".join(
                ["/home/ray/rayvens/rayvens/linux-x86_64",
                 os.getenv('PATH')])

        # Fail early before command is invoked if kamel is not found.
        if not utils.executableIsAvailable("kamel"):
            raise RuntimeError('kamel executable not found in PATH')

        # Fail if this is not a local command and kubectl is not found.
        if not kamel_utils.isLocalCommand(self.subcommand_type) and \
           not utils.executableIsAvailable("kubectl"):
            raise RuntimeError(
                "kubectl executable not found in PATH for non-local kamel"
                "command")

        # Get end condition or fail if command type is not supported.
        self.end_condition = kamel_utils.getKamelCommandEndCondition(
            self.subcommand_type, self.integration_name)

        # TODO: Does this work for Windows? Linux? Cloud?
        # Launch kamel command in a new process.
        self.process = subprocess.Popen(exec_command,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True,
                                        preexec_fn=os.setsid)

    def ongoing_command(self, message):
        if message is None:
            return self._check_successful_start()

        return self._check_logs(message)

    def returning_command(self):
        success = False
        for line in io.TextIOWrapper(self.process.stdout, encoding="utf-8"):
            line = line.strip()
            # Only output non-empty lines.
            if line != "":
                utils.printLog(self.subprocess_name, line)
            if self.end_condition in line:
                success = True

        # Log outcome.
        subcommand = kamel_utils.getKamelCommandString(self.subcommand_type)
        log = "Kamel `%s` command finished successfully." % subcommand
        if not success:
            log = "Kamel `%s` command failed." % subcommand
        utils.printLog(self.subprocess_name, log)

        # Delete intermediate file.
        if self.filename is not None:
            os.remove(self.filename)

        return success

    def getSubcommandType(self):
        return self.subcommand_type

    def getNamespace(self):
        return self.mode.getNamespace()

    def getMode(self):
        return self.mode

    def kill(self):
        # Magic formula for terminating all processes in the group including
        # any subprocesses that the kamel command might have created.
        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

    def _check_successful_start(self):
        # Check if kamel instance launched correctly.
        success = self._check_ongoing_process_output(self.end_condition, True)

        # Emit success/fail message.
        subcommand = kamel_utils.getKamelCommandString(self.subcommand_type)
        log = "Kamel `%s` command finished successfully." % subcommand
        if not success:
            log = "Kamel `%s` command failed." % subcommand
        utils.printLog(self.subprocess_name, log)

        # Delete intermediate file.
        if self.filename is not None:
            os.remove(self.filename)

        return success

    def _check_logs(self, message):
        # Check logs.
        success = self._check_ongoing_process_output(message)

        # Emit success/fail message.
        log = "Logs checked successfully."
        if not success:
            log = "Log check failed."
        utils.printLog(self.subprocess_name, log)
        return success

    def _check_ongoing_process_output(self, end_condition, with_output=False):
        success = False
        while True:
            # Log progress of kamel subprocess.
            output = utils.printLogFromSubProcess(self.subprocess_name,
                                                  self.process,
                                                  with_output=with_output)

            # Check process has not exited prematurely.
            if self.process.poll() is not None:
                break

            # Use the Kamel output to decide when Kamel instance is
            # ready to receive requests.
            if end_condition in output:
                success = True
                break

        return success


#
# Handle calls to Kubernetes kubectl.
#


class KubectlInvocation:
    subprocessName = "Kubectl"

    def __init__(self, commandOptions, k8sName=""):
        # If list is porvided, join it.
        if isinstance(commandOptions, list):
            commandOptions = " ".join(commandOptions)

        # Initialize state.
        self.subcommandType = kubernetes_utils.getKubectlCommandType(
            commandOptions)
        self.isRunning = False
        # TODO: rename this, this can be either a pod or a service or a
        # deployment name.
        self.podName = ""

        # Get end condition or fail if command type is not supported.
        self.endCondition = kubernetes_utils.getKubectlCommandEndCondition(
            self.subcommandType, k8sName)

        # Create the kubectl command.
        execCommand = " ".join(["exec", "kubectl", commandOptions])

        if not utils.executableIsAvailable("kubectl"):
            raise RuntimeError('kubectl executable not found in PATH')

        # Launch kamel command in a new process.
        self.process = subprocess.Popen(execCommand,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True,
                                        preexec_fn=os.setsid)

    def executeKubectlCmd(self,
                          message=None,
                          serviceName=None,
                          with_output=False):
        # Set end condition for custom message if one is provided.
        end_condition = self.endCondition
        if message is not None:
            end_condition = message

        # Check command output.
        success = self._check_ongoing_kubectl_output(end_condition,
                                                     serviceName, with_output)

        subcommand = kubernetes_utils.getKubectlCommandString(
            self.subcommandType)
        logMessage = "Kubectl %s command finished successfully." % subcommand
        if not success:
            logMessage = "Kubectl %s command failed." % subcommand
        utils.printLog(self.subprocessName, logMessage)

        return success

    def podIsInRunningState(self, integrationName):
        isRunning = False
        while True:
            # Process output line by line until we find the pod we are looking
            # for.
            # There should only be one new pod.
            output = utils.printLogFromSubProcess(self.subprocessName,
                                                  self.process,
                                                  with_output=True)
            if self.podName == "":
                self.podName = kubernetes_utils.extractPodFullName(
                    output, integrationName)

            if kubernetes_utils.isInRunningState(output, self.podName):
                isRunning = True
                break

            if kubernetes_utils.isInErrorState(output, self.podName):
                break

            # Return if command has exited.
            returnCode = self.process.poll()
            if returnCode is not None:
                break

        logMessage = "Pod with name `%s` is now Running." % self.podName
        if not isRunning:
            logMessage = "Pod with name `%s` failed to start." % self.podName
        utils.printLog(self.subprocessName, logMessage)

        return isRunning

    def getPodFullName(self):
        return self.podName

    def kill(self):
        # Terminating all processes in the group including any subprocesses
        # that the kubectl command might have created.
        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

    def _check_ongoing_kubectl_output(self,
                                      end_condition,
                                      serviceName=None,
                                      with_output=False):
        success = False
        while True:
            output = utils.printLogFromSubProcess(self.subprocessName,
                                                  self.process,
                                                  with_output=with_output)
            if self.subcommandType == \
               kubernetes_utils.KubectlCommand.GET_SERVICES:
                if kubernetes_utils.serviceNameMatches(output, serviceName):
                    success = True
                    break
            elif end_condition in output:
                success = True
                break

            returnCode = self.process.poll()
            if returnCode is not None:
                break
        return success
