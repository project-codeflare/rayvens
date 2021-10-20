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
import yaml
import rayvens.cli.utils as utils
import rayvens.cli.file as file
import rayvens.cli.java as java
import rayvens.cli.docker as docker
from rayvens.core.catalog import sources, sinks
from rayvens.core.catalog import construct_source, construct_sink
from rayvens.cli.docker import docker_push, docker_build


def build_base_image(args):
    # Create docker file for the base image.
    docker_image = docker.JavaAlpineDockerImage()

    # Install packages into the image.
    docker_image.install("maven")
    docker_image.install("bash")
    docker_image.install("curl")
    docker_image.update_installed_packages()

    # Bring in kamel executable:
    docker_image.add_kamel()

    # TODO: remove this, overwrite kamel executable with one from host.
    path_to_local_kamel = file.find_executable("kamel-linux")
    kamel_executable = file.File(path_to_local_kamel)
    docker_image.copy(kamel_executable, "/usr/local/bin/kamel")

    # Add kubernetes capabilities:
    docker_image.add_kubernetes()

    # Create preloader file with string content type:
    preload_file = file.File(java.preloader_file_name,
                             contents=java.preloader_file_contents)
    docker_image.copy(preload_file)

    # Add run command:
    docker_image.run(f"""kamel local run {preload_file.name} \
--dependency mvn:org.apache.camel.quarkus:camel-quarkus-java-joor-dsl; \
rm {preload_file.name}""")

    # Build image:
    docker_image.build(get_base_image_name(args))


def build_integration(args):
    # Create a work directory in the current directory:
    workspace_directory = file.create_workspace_directory()

    # Check if the source/sink is predefined.
    predefined_integration = args.kind is not None and (args.kind in sources
                                                        or args.kind in sinks)
    # By default the HTTP transport is used. This is the only supported
    # transport for now.
    inverted_transport = True

    # Put together the specification file.
    integration_file_path = None
    integration_file_name = None
    input_files = []
    if predefined_integration:
        # Get a skeleton configuration for this integration kind.
        base_config, _ = utils.get_current_config(args)

        # Create the integration yaml specification.
        route = "/" + args.kind + "-route"
        if args.kind in sources:
            spec = construct_source(base_config,
                                    f'platform-http:{route}',
                                    inverted=inverted_transport)
        else:
            spec = construct_sink(base_config, f'platform-http:{route}')

        # Write the specification to the file.
        integration_file_name = f'{args.kind + "-spec"}.yaml'
        input_files.append(integration_file_name)
        integration_file_path = workspace_directory.joinpath(
            integration_file_name)
        with open(integration_file_path, 'w') as f:
            modeline_options = utils.get_modeline_config(workspace_directory,
                                                         args,
                                                         run=False)
            f.write("\n".join(modeline_options) + "\n\n")
            f.write(yaml.dump(spec))

        # Check if additional files need to be added.
        input_files.extend(
            utils.add_additional_files(workspace_directory,
                                       predefined_integration, spec,
                                       inverted_transport))

        # Put together the summary file.
        summary_file_contents = utils.get_summary_file_contents(args)
        # print("Summary file contents:")
        # print(summary_file_contents)
        summary_file_name = 'summary.txt'
        summary_file_path = workspace_directory.joinpath(summary_file_name)
        with open(summary_file_path, 'w') as summary_file:
            summary_file.write(summary_file_contents)
    else:
        raise utils.clean_error_exit(workspace_directory,
                                     "Not implemented yet")

    # Resolve base image name:
    base_image = get_base_image_name(args)

    # Copy the current kubeconfig to the workspace directory:
    path_to_kubeconfig = os.path.expanduser('~') + "/.kube/config"
    file.copy_file(path_to_kubeconfig,
                   str(workspace_directory.joinpath("config")))

    # Write docker file contents:
    envvars = utils.get_modeline_envvars(workspace_directory, args)
    docker_file_contents = utils.get_integration_dockerfile(
        base_image,
        input_files,
        envvars=envvars,
        with_summary=True,
        preload_dependencies=True)
    print(docker_file_contents)
    docker_file_path = workspace_directory.joinpath("Dockerfile")
    with open(docker_file_path, mode='w') as docker_file:
        docker_file.write(docker_file_contents)

    # Put together the image name:
    integration_image = get_integration_image(args)

    # Build integration image:
    #   docker build workspace -t <image>
    docker_build(str(workspace_directory), integration_image)

    # Push base image to registry:
    #   docker push <image>
    docker_push(integration_image)

    # Clean-up
    file.delete_workspace_directory(workspace_directory)


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
