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

import os
import psutil
import signal
import subprocess
import sys

is_local = sys.argv[1] == "kamel"

# Start child process.
process = None
if is_local:
    process = subprocess.Popen(sys.argv[1:], start_new_session=True)
else:
    process = subprocess.Popen(sys.argv[3:], start_new_session=True)

# Wait for parent process.
psutil.wait_procs([psutil.Process().parent()])

# Terminate child process.
if is_local:
    if sys.platform == "win32":
        os.kill(process.pid, signal.CTRL_C_EVENT)
    else:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)

    # Delete integration file.
    os.remove(sys.argv[-1])
else:
    # TODO: Is the kamel run command kept alive somehow? kamel run is a
    # command that returns immediately. Investigate.
    # TODO: only run the delete command below if the integration exists.

    # Operator commands can only be terminated by running a kamel delete
    # command.
    command = ["kamel", "delete", sys.argv[1], "-n", sys.argv[2]]
    subprocess.Popen(command, start_new_session=True)
