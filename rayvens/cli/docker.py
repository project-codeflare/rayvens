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
import rayvens.cli.version as v
import rayvens.cli.file as file

image_workspace_name = "workspace"
local_workspace_name = "docker_workspace"
built_integration_directory = "my-integration"


def docker_run_integration(image_name,
                           local_integration_path,
                           integration_file_name,
                           envvars=[]):
    command = ["docker"]

    # Build command:
    command.append("run")

    # Mount integration file:
    # -v local_integration_path:inside_image_integration_path
    inside_image_integration_path = get_file_on_image(integration_file_name)

    # Mount argument:
    local_to_image_integration_mount = ":".join(
        [str(local_integration_path), inside_image_integration_path])

    if local_to_image_integration_mount is not None:
        command.append("-v")
        command.append(local_to_image_integration_mount)

    # Add env vars:
    for envvar in envvars:
        command.append("--env")
        command.append(f"{envvar}=${envvar}")

    # Add image:
    command.append(image_name)

    # Wait for docker command to finish before returning:
    print("Executing =>", " ".join(command))
    outcome = subprocess.run(command)

    if outcome.returncode == 0:
        print(f"Image {image_name} has been run successfully.")
    else:
        print(f"Image {image_name} run failed.")


def docker_build(working_directory, image_name):
    command = ["docker"]

    # Build command:
    command.append("build")

    # Path to working directory:
    command.append(working_directory)

    # Image name:
    command.append("-t")
    command.append(image_name)

    # Wait for docker command to finish before returning:
    outcome = subprocess.run(command)

    if outcome.returncode == 0:
        print(f"Base image {image_name} built successfully.")
    else:
        print(f"Base image {image_name} building failed.")


def docker_push(image_name):
    command = ["docker"]

    # Build command:
    command.append("push")

    # Image name:
    command.append(image_name)

    # Wait for docker command to finish before returning:
    outcome = subprocess.run(command)

    if outcome.returncode == 0:
        print(f"Base image {image_name} pushed successfully.")
    else:
        print(f"Base image {image_name} push failed.")


def docker_cp_to_host(container_id, from_file, to_file):
    command = ["docker"]

    # Copy command:
    command.append("cp")

    # Source:
    command.append(f"{container_id}:{from_file}")

    # Destination:
    command.append(f"{to_file}")

    # Wait for docker command to finish before returning:
    outcome = subprocess.run(command)

    if outcome.returncode == 0:
        print(f"Container file {from_file} successfully copied to host.")
    else:
        print(f"Container file {from_file} copy to host failed.")


def docker_create(image):
    command = ["docker"]

    # Copy command:
    command.append("create")

    # Source:
    command.append(image)

    # Wait for docker command to finish before returning:
    outcome = subprocess.run(command, stdout=subprocess.PIPE)

    if outcome.returncode == 0:
        print(f"Container for {image} created successfully.")
    else:
        print(f"Container creation for {image} failed.")

    return outcome.stdout.decode('utf8').strip()


def docker_rm(container_id):
    command = ["docker"]

    # Copy command:
    command.append("rm")

    # Source:
    command.append(container_id)

    # Wait for docker command to finish before returning:
    outcome = subprocess.run(command)

    if outcome.returncode == 0:
        print("Container removed successfully.")
    else:
        print("Container removal failed.")


class DockerCopyStep:
    def __init__(self, source, destination, from_stage, from_image):
        self.kind = "COPY"
        self.source = source
        self.destination = destination
        self.from_stage = from_stage
        self.from_image = from_image

    def emit(self):
        step = [self.kind]
        if self.from_stage is not None:
            if self.from_image is not None:
                raise RuntimeError("Ambiguous COPY source.")
            if not isinstance(self.from_stage, DockerStage):
                raise RuntimeError("Invalid from stage for COPY.")
            step.append("=".join(["--from", self.from_stage.stage_name]))
        if self.from_image is not None:
            step.append("=".join(["--from", self.from_image]))
        step.extend([self.source, self.destination])
        return " ".join(step)


class DockerRunStep:
    def __init__(self, instruction):
        self.kind = "RUN"
        self.instruction = instruction

    def emit(self):
        return " ".join([self.kind, self.instruction])


class DockerCmdStep:
    def __init__(self, command):
        self.kind = "CMD"
        self.command = command

    def emit(self):
        return " ".join([self.kind, self.command])


class DockerWorkdirStep:
    def __init__(self, work_directory):
        self.kind = "WORKDIR"
        self.work_directory = work_directory

    def emit(self):
        return " ".join([self.kind, self.work_directory])


class DockerStage:
    def __init__(self, image, stage_name):
        self.kind = "FROM"
        self.image = image
        self.stage_name = stage_name
        self.steps = []

    def add_step(self, step):
        self.steps.append(step)

    def emit(self):
        from_step = [self.kind, self.image]
        if self.stage_name is not None:
            from_step.extend(["AS", self.stage_name])
        stage = [" ".join(from_step)]
        for step in self.steps:
            stage.append(step.emit())
        return "\n".join(stage)


class DockerImage:
    def __init__(self, base_image=None):
        self.base_image = base_image
        self.docker_image_name = None
        self.stages = []
        self.command = None
        if self.base_image is not None:
            self.add_stage(self.base_image)
        self.current_stage = self.stages[-1]
        self.workspace_directory = file.Directory(local_workspace_name)
        self.os_type = None

    def copy(self, source, destination=".", from_stage=None, from_image=None):
        source_file = source
        if isinstance(source, file.File):
            self.add_file(source)
            source_file = source.name
        self.current_stage.add_step(
            DockerCopyStep(source_file, destination, from_stage, from_image))

    def run(self, instruction):
        self.current_stage.add_step(DockerRunStep(instruction))

    def cmd(self, command):
        self.current_stage.add_step(DockerCmdStep(command))

    def workdir(self, work_directory):
        self.current_stage.add_step(DockerWorkdirStep(work_directory))

    def add_stage(self, image, stage_name=None, previous_stage_name=None):
        if previous_stage_name is not None and len(self.stages) > 0:
            current_stage_name = self.current_stage.name
            if current_stage_name is None:
                self.current_stage.name = previous_stage_name
        new_stage = DockerStage(image, stage_name)
        self.stages.append(new_stage)
        self.current_stage = self.stages[-1]

    def add_file(self, host_file, sub_path=None):
        if not isinstance(host_file, file.File):
            raise RuntimeError("Invalid input file type, use File.")
        self.workspace_directory.add_file(host_file, sub_path=sub_path)

    def add_directory(self, directory):
        self.workspace_directory.add_directory(directory)

    def output_directory_structure(self, dockerfile_name="Dockerfile"):
        self.add_file(file.File(dockerfile_name, contents=self))
        self.workspace_directory.emit()

    def delete_directory_structure(self):
        self.workspace_directory.delete()

    def build(self, docker_image_name):
        self.output_directory_structure()
        self.docker_image_name = docker_image_name
        docker_build(self.workspace_directory.name, docker_image_name)
        self.delete_directory_structure()

    def push(self):
        if self.docker_image_name is None:
            raise RuntimeError(
                "Attempting to push an image that has not been built.")
        docker_push(self.docker_image_name)

    def emit(self):
        image = []
        for stage in self.stages:
            image.append(stage.emit())
        return "\n".join(image)

    def add_kubernetes(self):
        if self.os_type is None:
            raise RuntimeError(
                "Attempting to add kubectl in base docker image, "
                "consider using a derived docker image object with a "
                "specific OS type.")

    def add_kamel(self):
        if self.os_type is None:
            raise RuntimeError(
                "Attempting to add kamel executable in base docker image, "
                "consider using a derived docker image object with a "
                "specific OS type.")


# As a subclass of DockerImage this image has a particular OS type which
# determines the way things are installed and how paths are composed.
class JavaAlpineDockerImage(DockerImage):
    def __init__(self):
        DockerImage.__init__(self, base_image="adoptopenjdk/openjdk11:alpine")
        self.os_type = "linux"
        self.installed_packages = []

    def install(self, package):
        if package not in self.installed_packages:
            self.run("apk add --update " + package)
            self.installed_packages.append(package)

    def update_installed_packages(self):
        self.run("apk update && apk upgrade")

    def add_kubernetes(self):
        self.install("curl")
        self.run("curl -LO https://storage.googleapis.com/"
                 "kubernetes-release/release/`curl -s https://"
                 "storage.googleapis.com/kubernetes-release/release/"
                 "stable.txt`/bin/linux/amd64/kubectl")
        self.run("chmod +x ./kubectl")
        self.run("mv ./kubectl /usr/local/bin/")

    def add_kamel(self, version=None):
        kamel_version = v.kamel_version
        if version is not None:
            kamel_version = version
        self.copy("/usr/local/bin/kamel",
                  "/usr/local/bin/",
                  from_image="docker.io/apache/camel-k:" + kamel_version)


def add_summary_from_image(image, workspace_directory):
    # Create container from original image:
    container_id = docker_create(image)

    # Copy summary file from container to current workspace:
    docker_cp_to_host(container_id,
                      f"/{image_workspace_name}/{file.summary_file_name}", ".")

    # Remove container
    docker_rm(container_id)

    # Create a virtual summary file starting from the local file:
    summary_file = file.SummaryFile(file.summary_file_name)

    # Delete actual local file, the virtual file will continue to exist.
    summary_file.delete()

    # Add file to working directory:
    workspace_directory.add_file(summary_file)


def get_integration_directory_on_image():
    return "/".join([f"/{image_workspace_name}", built_integration_directory])


def get_routes_path_on_image(integration_file_name):
    directory = get_integration_directory_on_image()
    return "/".join([directory, "routes", integration_file_name])


def get_file_on_image(file_name):
    directory = get_integration_directory_on_image()
    return "/".join([directory, file_name])


def update_integration_file_in_image(file_name):
    copy_integration_file = ["cp"]
    copy_integration_file.append(get_file_on_image(file_name))
    copy_integration_file.append(get_routes_path_on_image(file_name))
    return " ".join(copy_integration_file)
