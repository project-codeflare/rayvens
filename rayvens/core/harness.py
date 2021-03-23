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

# start child process
process = subprocess.Popen(sys.argv[1:], start_new_session=True)

# wait for parent process
psutil.wait_procs([psutil.Process().parent()])

# kill child process
if sys.platform == "win32":
    os.kill(process.pid, signal.CTRL_C_EVENT)
else:
    os.killpg(os.getpgid(process.pid), signal.SIGKILL)

# delete integration file
os.remove(sys.argv[-1])
