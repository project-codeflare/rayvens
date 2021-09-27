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


def docker_run_integration(image_name,
                           local_integration_path,
                           integration_file_name,
                           envvars=[]):
    command = ["docker"]

    # Build command:
    command.append("run")

    # Mount integration file:
    # -v local_integration_path:inside_image_integration_path
    inside_image_integration_path = "/".join(
        ["/workspace", integration_file_name])

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
