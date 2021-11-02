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
from rayvens.cli.utils import PRINT

kamel_tag = "kamel"


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

    image_name = utils.get_base_image_name(args)

    if outcome.returncode == 0:
        PRINT(f"Base image {image_name} pushed successfully.", tag=kamel_tag)
    else:
        PRINT(f"Base image {image_name} push failed.", tag=kamel_tag)


def kamel_local_build_image(args, integration_file_path):
    command = ["kamel"]

    # Local command:
    command.append("local")

    # Build command:
    command.append("build")

    # Image:
    integration_image = utils.get_integration_image(args)
    command.append("--image")
    command.append(integration_image)

    # Add integration file:
    command.append(integration_file_path)

    # Wait for docker command to finish before returning:
    outcome = subprocess.run(command)

    if outcome.returncode == 0:
        PRINT(f"Base image {integration_image} pushed successfully.",
              tag=kamel_tag)
    else:
        PRINT(f"Base image {integration_image} push failed.", tag=kamel_tag)
