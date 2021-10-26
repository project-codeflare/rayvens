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
import rayvens.cli.file as file
import rayvens.cli.docker as docker
from rayvens.core.catalog import sources, sinks
from rayvens.core.catalog import construct_source, construct_sink
from rayvens.cli.docker import docker_run_integration


def run_integration(args):
    # Form full image name:
    if args.image is None:
        raise RuntimeError("No image name provided")
    registry = utils.get_registry(args)
    image = registry + "/" + args.image

    # Create a work directory in the current directory:
    workspace_directory = file.Directory("workspace")

    # Fetch summary file from integration image.
    docker.add_summary_from_image(image, workspace_directory)

    # Retrieve a reference to the summary file.
    summary_file = workspace_directory.get_file(file.summary_file_name)

    # Get integration kind from summary file:
    kind = summary_file.kind

    # Check if a valid launch image name has been passed:
    with_job_launcher = summary_file.launch_image != "None"

    # The name of the integration:
    name = kind
    if args.name is not None:
        name = args.name

    # Check if the source/sink is predefined.
    predefined_integration = kind in sources or kind in sinks

    # By default the HTTP transport is used. This is the only supported
    # transport for now.
    inverted_transport = True

    if predefined_integration:
        # Extract predefined integration kind:
        full_config = utils.get_full_config(summary_file, args)

        # Create the integration yaml specification.
        route = "/" + name + "-route"
        if kind in sources:
            spec = construct_source(full_config,
                                    f'platform-http:{route}',
                                    inverted=inverted_transport)
        else:
            spec = construct_sink(full_config, f'platform-http:{route}')

        # Write the specification to the file.
        modeline_options = utils.get_modeline_config(args, summary_file)
        integration_source_file = modeline_options + "\n\n" + yaml.dump(spec)
        integration_file = file.File(
            utils.get_kubernetes_integration_file_name(name),
            contents=integration_source_file)
    else:
        raise RuntimeError("Not implemented yet")

    # Fetch the variables specified as environment variables.
    envvars = utils.get_modeline_envvars(summary_file, args)

    if args.deploy is not None and args.deploy:
        # Set the namespace:
        namespace = "default"
        if args.namespace is not None:
            namespace = args.namespace

        # Deploy integration in Kubernetes:
        deployment = utils.get_deployment_yaml(name, namespace, args.image,
                                               utils.get_registry(args), args,
                                               with_job_launcher)

        # Create deployment file:
        deployment_file_name = utils.get_kubernetes_deployment_file_name(name)
        deployment_file = file.File(deployment_file_name, contents=deployment)
        workspace_directory.add_file(deployment_file)

        workspace_directory.emit()

        # Prepare Kubernetes API:
        from kubernetes import client, config
        import kubernetes.utils as kube_utils
        config.load_kube_config()

        # Call service creation:
        k8s_client = client.ApiClient()
        try:
            kube_utils.create_from_yaml(k8s_client,
                                        str(deployment_file.full_path))
        except kube_utils.FailToCreateError as creation_error:
            print("Failed to create deployment", creation_error)
        else:
            print(f"{name} successfully deployed in namespace {namespace}")

        workspace_directory.delete()
    else:
        # Run final integration image:
        #   docker run \
        #      -v integration_file_path:/workspace/<integration_file_name> \
        #      --env ENV_VAR=$ENV_VAR \
        #      <image>
        integration_file.emit()
        docker_run_integration(image,
                               integration_file.full_path,
                               integration_file.name,
                               envvars=envvars)
        integration_file.delete()
