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
import yaml
import sys
from rayvens.core import utils
from rayvens.core import kamel_utils
from rayvens.core import kubernetes_utils

#
# Kamel invocation.
#


class KamelInvocation:
    subprocess_name = "Kamel"

    def __init__(self,
                 command_options,
                 mode,
                 integration_name="",
                 integration_content=[]):
        self.mode = mode
        self.integration_name = integration_name

        # Get subcommand type.
        self.subcommand_type = kamel_utils.kamel_command_type(command_options)

        # Use an external harness process to handle graceful termination of
        # integrations.
        harness = os.path.join(os.path.dirname(__file__), 'harness.py')
        final_command = [sys.executable, harness]
        if self.subcommand_type == kamel_utils.KamelCommand.LOCAL_RUN:
            final_command.append('kamel')
        elif self.subcommand_type == kamel_utils.KamelCommand.RUN:
            final_command.extend(
                [self.integration_name, self.mode.namespace, 'kamel'])
        else:
            final_command = ['kamel']
        final_command.extend(command_options)

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

        # Log kamel command.
        print("Exec command => ", " ".join(final_command))

        # Add to PATH for case when this command is invoked in a cluster.
        if mode.is_cluster():
            os.environ['PATH'] = ":".join(
                ["/home/ray/rayvens/rayvens/linux-x86_64",
                 os.getenv('PATH')])

        # Fail early before command is invoked if kamel is not found.
        if self.uses_operator() and not utils.executable_is_available("kamel"):
            raise RuntimeError('kamel executable not found in PATH')

        # Get end condition or fail if command type is not supported.
        self.end_condition = kamel_utils.kamel_command_end_condition(
            self.subcommand_type, self.integration_name)

        # Launch kamel command in a new process.
        self.process = subprocess.Popen(final_command,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        start_new_session=True)

    def invoke(self, message):
        if message is None:
            return self._check_command_outcome()

        return self._check_logs(message)

    def runs_integration(self):
        return self.subcommand_type == kamel_utils.KamelCommand.RUN or \
            self.subcommand_type == kamel_utils.KamelCommand.LOCAL_RUN

    def uses_operator(self):
        return self.subcommand_type == kamel_utils.KamelCommand.RUN or \
            self.subcommand_type == kamel_utils.KamelCommand.LOG or \
            self.subcommand_type == kamel_utils.KamelCommand.INSTALL or \
            self.subcommand_type == kamel_utils.KamelCommand.DELETE

    def kill(self):
        # Magic formula for terminating all processes in the group including
        # any subprocesses that the kamel command might have created.
        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

    def cancel(self):
        try:
            os.kill(self.process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    def _check_command_outcome(self):
        # Check if kamel instance launched correctly.
        success = self._check_kamel_output(self.end_condition,
                                           with_output=True)

        # Emit success/fail message.
        subcommand = kamel_utils.kamel_command_str(self.subcommand_type)
        log = "Kamel `%s` command finished successfully." % subcommand
        if not success:
            log = "Kamel `%s` command failed." % subcommand
        utils.print_log(self.subprocess_name, log)

        # Delete intermediate file.
        if self.filename is not None:
            os.remove(self.filename)

        return success

    def _check_logs(self, message):
        # Check logs.
        success = self._check_kamel_output(message, with_output=True)

        # Emit success/fail message.
        log = "Logs checked successfully."
        if not success:
            log = "Log check failed."
        utils.print_log(self.subprocess_name, log)
        return success

    def _check_kamel_output(self, end_condition, with_output=False):
        while True:
            # Log progress of kamel subprocess:
            output = utils.print_log_from_subprocess(self.subprocess_name,
                                                     self.process.stdout,
                                                     with_output=with_output)

            # Use the Kamel output to decide when Kamel instance is
            # ready to receive requests.
            if end_condition in output:
                return True

            # Check process has not exited prematurely.
            if self.process.poll() is not None:
                break

        return False


#
# Handle calls to Kubernetes kubectl.
#


class KubectlInvocation:
    subprocess_name = "Kubectl"

    def __init__(self, command_options, service_name=""):
        # If list is porvided, join it.
        if isinstance(command_options, list):
            command_options = " ".join(command_options)

        # Initialize state.
        self.subcommand_type = kubernetes_utils.kubectl_command_type(
            command_options)
        self.pod_name = ""

        # Get end condition or fail if command type is not supported.
        self.end_condition = kubernetes_utils.kamel_command_end_condition(
            self.subcommand_type, service_name)

        # Create the kubectl command.
        command = " ".join(["exec", "kubectl", command_options])

        if not utils.executable_is_available("kubectl"):
            raise RuntimeError('kubectl executable not found in PATH')

        # Launch kamel command in a new process.
        self.process = subprocess.Popen(command,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True,
                                        preexec_fn=os.setsid)

    def invoke(self, message, service_name, with_output=False):
        # Set end condition for custom message if one is provided.
        end_condition = self.end_condition
        if message is not None:
            end_condition = message

        # Check command output.
        success = self._check_kubectl_output(end_condition,
                                             service_name=service_name,
                                             with_output=with_output)

        subcommand = kubernetes_utils.kubectl_command_str(self.subcommand_type)
        log = "Kubectl %s command finished successfully." % subcommand
        if not success:
            log = "Kubectl %s command failed." % subcommand
        utils.print_log(self.subprocess_name, log)

        return success

    def pod_is_running(self, integration_name):
        running = False
        while True:
            # Process output line by line until we find the pod we are looking
            # for.
            # There should only be one new pod.
            output = utils.print_log_from_subprocess(self.subprocess_name,
                                                     self.process.stdout,
                                                     with_output=True)
            if self.pod_name == "":
                self.pod_name = kubernetes_utils.extract_pod_name(
                    output, integration_name)

            if kubernetes_utils.is_pod_state_running(output, self.pod_name):
                running = True
                break

            if kubernetes_utils.is_pod_state_error(output, self.pod_name):
                break

            # Return if command has exited.
            if self.process.poll() is not None:
                break

        log = "Pod with name `%s` is now Running." % self.pod_name
        if not running:
            log = "Pod with name `%s` failed to start." % self.pod_name
        utils.print_log(self.subprocess_name, log)

        return running

    def kill(self):
        # Terminating all processes in the group including any subprocesses
        # that the kubectl command might have created.
        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

    def _check_kubectl_output(self,
                              end_condition,
                              service_name=None,
                              with_output=False):
        success = False
        while True:
            output = utils.print_log_from_subprocess(self.subprocess_name,
                                                     self.process.stdout,
                                                     with_output=with_output)
            if self.subcommand_type == \
               kubernetes_utils.KubectlCommand.GET_SERVICES:
                if kubernetes_utils.service_name_matches(output, service_name):
                    success = True
                    break
            elif end_condition in output:
                success = True
                break

            if self.process.poll() is not None:
                break
        return success


#
# Kafka topic creator invocation.
#


class KafkaInvocation:
    subprocess_name = "Kafka"

    def __init__(self, command_options):
        final_command = ['kafka-topics']
        final_command.extend(command_options)

        # Log kamel command.
        print("Exec command => ", " ".join(final_command))

        # Launch kafka command in a new process.
        self.process = subprocess.Popen(final_command,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        start_new_session=True)

    def invoke(self, checked_topic):
        return self._check_kafka_output(checked_topic)

    def _check_kafka_output(self, checked_topic):
        while True:
            # Log progress of kafka topic creation subprocess:
            output = utils.print_log_from_subprocess(self.subprocess_name,
                                                     self.process.stdout,
                                                     with_output=True)
            if checked_topic is not None and checked_topic in output:
                return True

            if checked_topic is None and "Created topic" in output:
                return True

            if checked_topic is None and "already exists" in output:
                return True

            # Check process has not exited prematurely.
            if self.process.poll() is not None:
                break

        return False
