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
import pathlib
import platform
import subprocess


def create_workspace_directory(remove_previous=True):
    workspace_directory = pathlib.Path.cwd().joinpath("workspace")
    if remove_previous and os.path.isdir(workspace_directory):
        delete_workspace_directory(workspace_directory)
    os.mkdir(workspace_directory)
    return workspace_directory


def delete_workspace_directory(workspace_directory):
    if os.path.isdir(workspace_directory):
        for file in workspace_directory.iterdir():
            os.remove(file)
        os.rmdir(workspace_directory)


def find_executable(executable_name):
    command = ["which"]
    if platform.system() == "Windows":
        command = ["where"]
    command.append(executable_name)
    return subprocess.check_output(command).decode('utf8').strip()


def copy_file(source, destination):
    command = ["cp"]
    if platform.system() == "Windows":
        command = ["copy"]
    command.append(source)
    command.append(destination)
    subprocess.call(command)
