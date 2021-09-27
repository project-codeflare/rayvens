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

import yaml
import rayvens.cli.utils as utils
from rayvens.core.catalog import sources, sinks
from rayvens.core.catalog import construct_source, construct_sink
from rayvens.cli.docker import docker_create, docker_rm, docker_cp_to_host
from rayvens.cli.docker import docker_run_integration


def run_integration(args):
    # Create a work directory in the current directory:
    workspace_directory = utils.create_workspace_dir()

    # Get registry:
    registry = utils.get_registry(args)

    # Form full image name:
    if args.image is None:
        utils.clean_error_exit(workspace_directory, "No image name provided")
    image = registry + "/" + args.image

    # Create container from original image:
    container_id = docker_create(image)

    # Copy summary file from container to current workspace:
    docker_cp_to_host(container_id, "/workspace/summary.txt",
                      workspace_directory)

    # Remove container
    docker_rm(container_id)

    # Get integration kind from summary file:
    kind = utils.summary_get_kind(workspace_directory)

    # Check if the source/sink is predefined.
    predefined_integration = kind in sources or kind in sinks

    # By default the HTTP transport is used. This is the only supported
    # transport for now.
    inverted_transport = True

    if predefined_integration:
        # Extract predefined integration kind:
        full_config = utils.get_full_config(workspace_directory, args)

        # Create the integration yaml specification.
        route = "/" + kind + "-route"
        if kind in sources:
            spec = construct_source(full_config,
                                    f'platform-http:{route}',
                                    inverted=inverted_transport)
        else:
            spec = construct_sink(full_config, f'platform-http:{route}')

        # Write the specification to the file.
        integration_file_name = f'{kind + "-spec"}.yaml'
        integration_file_path = workspace_directory.joinpath(
            integration_file_name)
        with open(integration_file_path, 'w') as f:
            # Dump modeline options:
            modeline_options = utils.get_modeline_config(
                workspace_directory, args)
            f.write("\n".join(modeline_options) + "\n\n")
            f.write(yaml.dump(spec))

        with open(integration_file_path, 'r') as f:
            print(f.read())
    else:
        utils.clean_error_exit(workspace_directory, "Not implemented yet")

    # Fetch the variables specified as environment variables.
    envvars = utils.get_modeline_envvars(workspace_directory, args)

    # Run final integration image:
    #   docker run \
    #      -v integration_file_path:/workspace/<integration_file_name> \
    #      --env ENV_VAR=$ENV_VAR \
    #      <image>
    docker_run_integration(image,
                           integration_file_path,
                           integration_file_name,
                           envvars=envvars)

    # Clean-up
    utils.delete_workspace_dir(workspace_directory)
