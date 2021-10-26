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
    docker_image.build(utils.get_base_image_name(args))


def build_integration(args):
    # Create image for integration:
    docker_image = docker.DockerImage(utils.get_base_image_name(args))

    # Create workspace inside the image.
    docker_image.run(f"mkdir -p /{docker.image_workspace_name}")
    docker_image.workdir(f"/{docker.image_workspace_name}")

    # Create the yaml source for the integration locally and transfer it
    # to the image.
    predefined_integration = args.kind is not None and (args.kind in sources
                                                        or args.kind in sinks)
    inverted_transport = True
    launches_kubectl_jobs = args.launch_image is not None

    # Put together the summary file.
    summary_file = utils.get_summary_file(args)

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

        # Any command line specified properties get transformed into modeline
        # options. Modeline options live at the top of the integration source
        # file.
        modeline_options = utils.get_modeline_config(args)
        integration_source_file = modeline_options + "\n\n" + yaml.dump(spec)
        integration_file = file.File(f'{args.kind + "-spec"}.yaml',
                                     contents=integration_source_file)
        docker_image.copy(integration_file)

        # Check if additional files need to be added.
        additional_files = utils.get_additional_files(spec, inverted_transport,
                                                      args.launch_image)
        for additional_file in additional_files:
            docker_image.copy(additional_file)

        # Add summary file to image.
        docker_image.copy(summary_file)
    else:
        raise RuntimeError("Not implemented yet")

    # Copy the current kubeconfig to the workspace directory:
    if launches_kubectl_jobs:
        path_to_kubeconfig = os.path.expanduser('~') + "/.kube/config"
        kubeconfig_file = file.File(path_to_kubeconfig)
        docker_image.copy(kubeconfig_file)

    # Additional files to be added to the RUN command line:
    files_list = " ".join(
        [additional_file.name for additional_file in additional_files])

    # Command that is run when building the image. This command is meant
    # to preload all dependencies to run the integration.
    run_command = f"""kamel local build {integration_file.name} {files_list} \
--integration-directory my-integration \
--dependency mvn:org.apache.camel.quarkus:camel-quarkus-java-joor-dsl \
--dependency mvn:com.googlecode.json-simple:json-simple:1.1.1"""
    if launches_kubectl_jobs:
        run_command += " --dependency mvn:io.kubernetes:client-java:11.0.0"
    docker_image.run(run_command)

    # List of all environment variables either given on the command line
    # or as part of the summary file or are part of the inner image scope
    # and are relevant to kamel local run.
    envvars = utils.get_modeline_envvars(summary_file, args)
    if launches_kubectl_jobs:
        envvars.extend([
            "PATH", "KUBERNETES_SERVICE_PORT", "KUBERNETES_PORT", "HOSTNAME",
            "JAVA_VERSION", "KUBERNETES_PORT_443_TCP_ADDR",
            "KUBERNETES_PORT_443_TCP_PORT", "KUBERNETES_PORT_443_TCP_PROTO",
            "LANG", "HTTP_SOURCE_ENTRYPOINT_PORT", "KUBERNETES_PORT_443_TCP",
            "KUBERNETES_SERVICE_PORT_HTTPS", "LC_ALL", "JAVA_HOME",
            "KUBERNETES_SERVICE_HOST", "PWD"
        ])

    # The list of envvars is of the format:
    #   --env ENV_VAR=$ENV_VAR
    outer_scope_envvars = []
    for envvar in envvars:
        outer_scope_envvars.append(f"--env {envvar}=${envvar}")
    outer_scope_envvars = " ".join(outer_scope_envvars)

    docker_image.cmd("kamel local run --integration-directory my-integration "
                     f"{outer_scope_envvars}")

    # Build image.
    docker_image.build(utils.get_integration_image(args))

    # Push base image to registry.
    docker_image.push()
