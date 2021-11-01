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
import rayvens.cli.utils as utils

summary_file_name = "summary.txt"


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

    def delete(self):
        # TODO: keep track of all places where the file was emitted
        # and then when delete is invoked, remove the file from
        # all those locations.
        try:
            if self.exists_on_file_system():
                os.remove(self.full_path)
        except OSError as e:
            print("Error: %s : %s" % (self.full_path, e.strerror))

    def get_contents(self):
        if isinstance(self.contents, str):
            return self.contents
        if not hasattr(self.contents, "emit"):
            raise RuntimeError(
                "Non-string file contents must have emit method.")
        return self.contents.emit()

    def emit(self):
        if self.contents is not None:
            with open(self.full_path, mode='w') as fs_file:
                fs_file.write(self.get_contents())
        elif os.path.isfile(self.original_full_path):
            if self.original_full_path != self.full_path:
                copy_file(str(self.original_full_path), str(self.full_path))
        else:
            raise RuntimeError(f"Cannot emit file: {str(self.full_path)}")

    def exists_on_file_system(self):
        return os.path.isfile(self.full_path)

    def original_exists_on_file_system(self):
        return os.path.isfile(self.original_full_path)

    def read(self):
        file_contents = None
        if not self.original_exists_on_file_system():
            return file_contents
        with open(self.original_full_path, 'r') as f:
            file_contents = f.read()
        return file_contents


class Directory(FileSystemObject):
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
        if sub_path is None and self.already_added(file) and not override:
            raise RuntimeWarning(
                f"A file with name {file.name} already added to "
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

    # Checks if a file has already been added to the list of files this
    # directory holds.
    def already_added(self, file):
        for existing_file in self.files:
            if existing_file.name == file.name:
                return True
        return False

    # Returns the first time it finds a file in the directory hierarchy.
    def get_file(self, file_name):
        for file in self.files:
            if file.name == file_name:
                return file
        for sub_directory in self.sub_directories:
            found_file = sub_directory.get_file_reference()
            if found_file is not None:
                return found_file
        return None


class SummaryFile(File):
    def __init__(self, path=None):
        self.kind = None
        self.launch_image = None
        self.properties = {}
        self.envvars = {}
        self._property_prefix = "property: "
        self._envvar_prefix = "envvar: "
        if path is None:
            File.__init__(self, summary_file_name, contents=None)
        else:
            File.__init__(self, path, contents=None)
            self.parse()

    def add_property(self, property_name, property_value):
        self.properties[property_name] = property_value

    def add_envvar(self, property_name, envvar):
        self.envvars[property_name] = envvar

    def get_envvars(self):
        return [key for key in self.envvars]

    def get_properties(self):
        return [key for key in self.properties]

    def parse(self):
        if not self.original_exists_on_file_system():
            raise RuntimeError(
                "Parsed summary file is not on the file system.")
        # Get kind:
        self.kind = utils._get_field_from_summary(self.original_full_path,
                                                  "kind")
        self.launch_image = utils._get_field_from_summary(
            self.original_full_path, "launch_image")
        valid_properties = utils.get_all_properties(self.kind)
        for property_name in valid_properties:
            # Property is of type:
            # property: <property_name>=<value>
            value = utils._get_field_from_summary(self.original_full_path,
                                                  property_name,
                                                  prefix=self._property_prefix)
            if value is not None:
                self.add_property(property_name, value)
            # Envvar is of type:
            # property: <property_name>=<envvar>
            envvar = utils._get_field_from_summary(self.original_full_path,
                                                   property_name,
                                                   prefix=self._envvar_prefix)
            if envvar is not None:
                self.add_envvar(property_name, envvar)

    def emit(self):
        summary = []
        summary.append(f"kind={self.kind}")
        if self.launch_image is not None:
            summary.append(f"launch_image={self.launch_image}")
        else:
            summary.append("launch_image=None")
        for prop in self.properties:
            summary.append(
                f"{self._property_prefix}{prop}={self.properties[prop]}")
        for prop in self.envvars:
            summary.append(f"{self._envvar_prefix}{prop}={self.envvars[prop]}")
        self.contents = "\n".join(summary)
        File.emit(self)


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
