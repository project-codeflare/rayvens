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
import rayvens.cli.utils as utils


def kamel_local_build_base_image(args):
    command = ["kamel"]

    # Local command:
    command.append("local")

    # Build command:
    command.append("build")

    # Base image options:
    command.append("--base-image")

    # Registry:
    registry = utils.get_registry(args)
    command.append("--container-registry")
    command.append(registry)

    # Wait for docker command to finish before returning:
    outcome = subprocess.run(command)

    image_name = get_base_image_name(args)

    if outcome.returncode == 0:
        print(f"Base image {image_name} pushed successfully.")
    else:
        print(f"Base image {image_name} push failed.")


def kamel_local_build_image(args, integration_file_path):
    command = ["kamel"]

    # Local command:
    command.append("local")

    # Build command:
    command.append("build")

    # Image:
    integration_image = get_integration_image(args)
    command.append("--image")
    command.append(integration_image)

    # Add integration file:
    command.append(integration_file_path)

    # Wait for docker command to finish before returning:
    outcome = subprocess.run(command)

    if outcome.returncode == 0:
        print(f"Base image {integration_image} pushed successfully.")
    else:
        print(f"Base image {integration_image} push failed.")


def get_base_image_name(args):
    # Registry name:
    registry = utils.get_registry(args)

    # Base image name:
    return registry + "/" + utils.base_image_name


def get_integration_image(args):
    # Registry name:
    registry = utils.get_registry(args)

    # Actual image name:
    image_name = args.kind + "-image"
    if args.image is not None:
        image_name = args.image

    # Integration image name:
    return registry + "/" + image_name
