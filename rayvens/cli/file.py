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


class FileSystemObject:
    def __init__(self, path_to_file):
        if path_to_file is None:
            raise RuntimeError("Path to file is None.")
        self.full_path = path_to_file
        if isinstance(path_to_file, str):
            self.full_path = pathlib.Path(path_to_file)
        self.name = self.full_path.name
        self.path = self.full_path.parent
        if self.path == pathlib.Path('.'):
            self.path = pathlib.Path.cwd()
            self.full_path = self.path.joinpath(self.name)

    def move(self, path):
        if path is not None and isinstance(path, str):
            path = pathlib.Path(path)
        self.path = path
        self.full_path = self.path.joinpath(self.name)

    def rename(self, name):
        self.name = name
        self.full_path = self.path.joinpath(self.name)


class File(FileSystemObject):
    def __init__(self, path, contents=None):
        FileSystemObject.__init__(self, path)
        self.contents = contents
        self.original_name = self.name
        self.original_full_path = self.full_path
        self.file_exists = self.contents is None

    def delete(self):
        try:
            os.remove(self.full_path)
        except OSError as e:
            print("Error: %s : %s" % (self.full_path, e.strerror))

    def emit(self):
        if self.contents is not None:
            with open(self.full_path, mode='w') as fs_file:
                if isinstance(self.contents, str):

                    fs_file.write(self.contents)
                else:
                    if not hasattr(self.contents, "emit"):
                        raise RuntimeError(
                            "Non-string file contents must have emit method.")
                    fs_file.write(self.contents.emit())
        elif os.path.isfile(self.original_full_path):
            if self.original_full_path != self.full_path:
                copy_file(str(self.original_full_path), str(self.full_path))
        else:
            raise RuntimeError(f"Cannot emit file: {str(self.full_path)}")


class Directory:
    def __init__(self, path):
        FileSystemObject.__init__(self, path)
        self.files = []
        self.sub_directories = []

    def move(self, path):
        FileSystemObject.move(self, path)
        for file in self.files:
            file.move(self.full_path)

    def add_file(self, file, sub_path=None, override=False):
        if not isinstance(file, File):
            raise RuntimeError("Invalid file object type provided, use File.")
        if sub_path is None and self.file_exists(file) and not override:
            raise RuntimeWarning(
                f"A file with name {file.name} already exists in "
                f"directory {self.full_path}")
        if sub_path is not None and not isinstance(sub_path, str):
            raise RuntimeError("Invalid sub_path type provided, use string.")
        if sub_path is not None:
            path_components = sub_path.split(os.path.sep)
            found_sub_directory = False
            for sub_directory in self.sub_directories:
                if path_components.name == path_components[0]:
                    found_sub_directory = True
                    new_sub_path = None
                    if len(path_components) > 1:
                        new_sub_path = os.path.sep.join(path_components[1:])
                    sub_directory.add_file(file, sub_path=new_sub_path)
            if not found_sub_directory:
                raise RuntimeError(
                    f"Subpath subdirectory {path_components[0]} not found.")
        else:
            file.move(self.full_path)
            self.files.append(file)

    def add_directory(self, directory):
        if not isinstance(directory, Directory):
            raise RuntimeError(
                "Invalid directory object type provided, use Directory.")
        directory.move(self.full_path)
        self.sub_directories.append(directory)

    def delete(self):
        for file in self.files:
            file.delete()
        for directory in self.sub_directories:
            directory.delete()
        try:
            self.full_path.rmdir()
        except OSError as e:
            print("Error: %s : %s" % (self.full_path, e.strerror))

    def emit(self, replace=True):
        # if replace and os.path.isdir(self.full_path):
        #     self.delete()
        os.mkdir(self.full_path)
        for file in self.files:
            file.emit()
        for directory in self.sub_directories:
            directory.emit()

    def file_exists(self, file):
        for existing_file in self.files:
            if existing_file.name == file.name:
                return True
        return False


# REMOVE
def create_workspace_directory(remove_previous=True):
    workspace_directory = pathlib.Path.cwd().joinpath("workspace")
    if remove_previous and os.path.isdir(workspace_directory):
        delete_workspace_directory(workspace_directory)
    os.mkdir(workspace_directory)
    return workspace_directory


# REMOVE
def delete_workspace_directory(workspace_directory):
    if os.path.isdir(workspace_directory):
        for file in workspace_directory.iterdir():
            os.remove(file)
        os.rmdir(workspace_directory)


# REMOVE
def write_file(file_path, contents):
    with open(file_path, mode='w') as file:
        file.write(contents)


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
