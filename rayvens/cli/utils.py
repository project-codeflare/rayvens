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

# import yaml
import rayvens.cli.file as file
import rayvens.cli.kubernetes as kube
import rayvens.cli.java as java
from rayvens.core.catalog_utils import get_all_properties
from rayvens.core.catalog_utils import integration_requirements
from rayvens.core.catalog_utils import get_modeline_properties
from rayvens.core.catalog_utils import fill_config
from rayvens.core import catalog_utils

base_image_name = "integration-base"
kube_proxy_image_name = "kube-proxy"
property_prefix = "property: "
envvar_prefix = "envvar: "
job_launcher_service_account = "job-launcher-service-account"
job_launcher_cluster_role_binding = "job-launcher-service-account"
job_manager_role = "job-manager-role"


def get_deployment_yaml(name, namespace, image_name, registry, args,
                        with_job_launcher):
    # Kubernetes deployment options:
    replicas = 1
    full_image_name = image_name
    if registry is not None:
        full_image_name = "/".join([registry, image_name])

    integration_name = get_kubernetes_integration_name(name)
    entrypoint_name = get_kubernetes_entrypoint_name(name)
    label_name = get_kubernetes_label_name(name)

    # TODO: these deployment options work with a local Kubernetes cluster
    # with a local registry i.e. localhost:5000. Test with actual cluster.

    container = kube.Container(image_name,
                               full_image_name,
                               image_pull_policy="Always")

    combined_configuration = []

    if with_job_launcher:
        # Service account for the job lunch permissions:
        service_account = kube.ServiceAccount(job_launcher_service_account,
                                              namespace)
        combined_configuration.append(service_account.configuration())

        # Create the cluster role specifying the resource type and the
        # allowable actions (verbs). By default all verbs are enabled if
        # none are specified.
        cluster_role = kube.ClusterRole(job_manager_role, namespace)
        cluster_role.add_rule("jobs")
        combined_configuration.append(cluster_role.configuration())

        # Create a cluster role binding between the service account and
        # the cluster role defined above.
        cluster_role_binding = kube.ClusterRoleBinding(
            job_launcher_cluster_role_binding, [service_account], cluster_role)
        combined_configuration.append(cluster_role_binding.configuration())

    # Assemble the pod that the deployment will be managing.
    managed_pod = kube.Pod("managed_pod", namespace)

    # Ensure the pod has the ability to launch jobs by addint the service
    # account created above.
    if with_job_launcher:
        managed_pod.add_service_account(service_account)
    managed_pod.add_container(container)
    managed_pod.add_label("integration", label_name)

    # Create the deployment.
    deployment = kube.Deployment(integration_name,
                                 managed_pod,
                                 namespace=namespace,
                                 replicas=replicas)

    # Create a NodePort service to enable outside communication.
    node_port_spec = kube.NodePortSpec()
    node_port_spec.add_selector("integration", label_name)
    node_port_spec.add_port(3000, 30001)
    service = kube.Service(entrypoint_name,
                           node_port_spec,
                           namespace=namespace)
    # Add the service to the deployment.
    deployment.add_service(service)

    combined_configuration.append(deployment.configuration())

    # print("\n---\n".join(combined_configuration))
    return "\n---\n".join(combined_configuration)


def get_summary_file(args):
    integration_summary = file.SummaryFile()

    integration_summary.kind = args.kind
    integration_summary.launch_image = args.launch_image

    if args.properties is not None:
        config, missing_property_value = fill_config(args.kind,
                                                     args.properties,
                                                     show_missing=False)
        for key in config:
            if key not in missing_property_value:
                integration_summary.add_property(key, config[key])

    envvars = get_current_envvars(args)
    for property_key in envvars:
        integration_summary.add_envvar(property_key, envvars[property_key])

    return integration_summary


def _create_file(workspace_directory, file_name, file_contents):
    file_processor_file_path = workspace_directory.joinpath(file_name)
    with open(file_processor_file_path, 'w') as f:
        f.write(file_contents)
    return file_name


def get_additional_files(spec, inverted_transport, launch_image):
    files = []
    if catalog_utils.integration_requires_file_processor(spec):
        files.append(
            file.File("ProcessFile.java",
                      contents=java.get_process_file_contents()))

    if catalog_utils.integration_requires_path_processor(spec):
        files.append(
            file.File("ProcessPath.java",
                      contents=java.get_process_path_contents()))

    # Write the Java queue code to the file when using HTTP transport.
    if inverted_transport:
        if catalog_utils.integration_requires_file_queue(spec):
            files.append(
                file.File("FileQueue.java",
                          contents=java.get_java_file_queue_contents()))

        if catalog_utils.integration_requires_file_queue(spec):
            files.append(
                file.File("FileQueueJson.java",
                          contents=java.get_java_file_queue_json_contents()))

        if catalog_utils.integration_requires_file_watch_queue(spec):
            files.append(
                file.File("FileWatchQueue.java",
                          contents=java.get_java_file_watch_queue_contents()))

        if catalog_utils.integration_requires_meta_event_queue(spec):
            files.append(
                file.File("MetaEventQueue.java",
                          contents=java.get_java_meta_event_queue_contents()))

        if catalog_utils.integration_requires_queue(spec):
            files.append(
                file.File("Queue.java",
                          contents=java.get_java_queue_contents(launch_image)))
    return files


def get_registry(args):
    # Registry name:
    registry = None
    if args.dev is not None:
        registry = "localhost:5000"
    else:
        raise RuntimeError(
            "the --dev flag is required for `rayvens base` call")

    return registry


def get_given_properties(args):
    given_properties = []
    if args.properties is not None and len(args.properties) > 0:
        for property_value in args.properties:
            components = property_value.split("=")
            given_properties.append(components[0])
    return given_properties


def get_given_property_envvars(args):
    given_envvars = []
    if args.envvars is not None and len(args.envvars) > 0:
        for property_value in args.envvars:
            components = property_value.split("=")
            given_envvars.append(components[0])
    return given_envvars


def get_given_envvars(args):
    given_envvars = []
    if args.envvars is not None and len(args.envvars) > 0:
        for property_value in args.envvars:
            components = property_value.split("=")
            given_envvars.append("=".join(components[1:]))
    return given_envvars


def check_properties(kind, properties):
    invalid_props = []
    valid_properties = get_all_properties(kind)
    for property_name in properties:
        if property_name not in valid_properties:
            invalid_props.append(property_name)
    return invalid_props


def summary_file_path(workspace_directory):
    return workspace_directory.joinpath("summary.txt")


def _get_field_from_summary(summary_file_path, field, prefix=None):
    result = None
    with open(summary_file_path, "r") as summary:
        for line in summary.readlines():
            if prefix is not None:
                if not line.startswith(prefix):
                    continue
                line = line[len(prefix):]

            components = line.split("=")
            if components[0] == field:
                result = "=".join(components[1:])
                break

    if result is None:
        return None

    return result.strip()


def summary_get_kind(workspace_directory):
    summary_path = summary_file_path(workspace_directory)
    return _get_field_from_summary(summary_path, "kind")


def summary_get_envvar_properties(kind, summary_file, given_envvars):
    envvars = []
    valid_properties = get_all_properties(kind)
    for property_name in valid_properties:
        if property_name not in given_envvars and \
           property_name in summary_file.envvars:
            property_value = summary_file.envvars[property_name]
            if property_value is not None:
                envvars.append(f"{property_name}={property_value}")
    return envvars


def summary_get_envvars(kind, workspace_directory):
    envvars = []
    summary_path = summary_file_path(workspace_directory)
    valid_properties = get_all_properties(kind)
    for property_name in valid_properties:
        property_value = _get_field_from_summary(summary_path,
                                                 property_name,
                                                 prefix=envvar_prefix)
        if property_value is not None:
            envvars.append(property_value)
    return envvars


def summary_get_properties(kind, summary_file, given_properties):
    properties = []
    valid_properties = get_all_properties(kind)
    for property_name in valid_properties:
        if property_name not in given_properties and \
           property_name in summary_file.properties:
            property_value = summary_file.properties[property_name]
            if property_value is not None:
                properties.append(f"{property_name}={property_value}")
    return properties


def get_current_envvars(args):
    envvars = {}
    if args.envvars is not None and len(args.envvars) > 0:
        for property_env_pair in args.envvars:
            components = property_env_pair.split("=")
            envvars[components[0]] = "=".join(components[1:])
    return envvars


def get_current_config(args):
    requirements = integration_requirements(args.kind)

    config = dict(kind=args.kind)

    # Fill in properties if any have been provided.
    missing_requirements = []
    if args.properties is not None and len(args.properties) > 0:
        config, _ = fill_config(args.kind, args.properties, show_missing=False)

    # Fill in environment-based properties if any have been provided.
    if args.envvars is not None and len(args.envvars) > 0:
        for property_env_pair in args.envvars:
            components = property_env_pair.split("=")
            config[components[0]] = "=".join(components[1:])

    if len(requirements['required']) > 0:
        for req_property in requirements['required']:
            if req_property not in config:
                missing_requirements.append(req_property)
                config[req_property] = "missing_property_value"

    return config, missing_requirements


def get_full_config(summary_file, args):
    # Get the kind of the integration:
    kind = summary_file.kind

    # Get properties given as args:
    given_properties = get_given_properties(args)

    # Validate user-given properties:
    invalid_props = check_properties(kind, given_properties)
    if len(invalid_props) > 0:
        invalid_props = " ".join(invalid_props)
        raise RuntimeError(f"Invalid properties provided: {invalid_props}")

    # Assemble list of all property-value pairs:
    properties = []
    if args.properties is not None:
        properties = args.properties
    properties.extend(
        summary_get_properties(kind, summary_file, given_properties))

    # Fill configuration with values:
    config, _ = fill_config(kind, properties, show_missing=False)
    return config


def get_modeline_config(args, summary_file=None):
    # Get the kind of the integration:
    if summary_file is not None:
        kind = summary_file.kind
    else:
        kind = args.kind

    # Get envvars given as args:
    given_envvars = get_given_property_envvars(args)

    # Validate user-given envvars:
    invalid_props = check_properties(kind, given_envvars)
    if len(invalid_props) > 0:
        invalid_props = " ".join(invalid_props)
        raise RuntimeError(f"Invalid properties provided: {invalid_props}")

    # Assemble list of all property-value envvar pairs:
    envvars = []
    if args.envvars is not None:
        envvars = args.envvars
    if summary_file is not None:
        envvars.extend(
            summary_get_envvar_properties(kind, summary_file, given_envvars))

    # Transform configuarion in list of modeline properties:
    modeline_properties = get_modeline_properties(kind, envvars)
    result = []
    for key in modeline_properties:
        result.append(modeline_properties[key])
    return "\n".join(result)


def get_modeline_envvars(summary_file, args):
    # Get envvars given as args:
    given_envvars = get_given_envvars(args)

    # Get envvars from summary file:
    given_envvars.extend(summary_file.get_envvars())
    return given_envvars


def get_kubernetes_deployment_file_name(name):
    return f"{name}-deployment.yaml"


def get_kubernetes_integration_name(name):
    return f"{name}-integration"


def get_kubernetes_integration_file_name(name):
    return f"{name}-integration.yaml"


def get_kubernetes_entrypoint_name(name):
    return f"{name}-entrypoint"


def get_kubernetes_label_name(name):
    return f"{name}-label"


def get_base_image_name(args):
    # Registry name:
    registry = get_registry(args)

    # Base image name:
    return registry + "/" + base_image_name


def get_integration_image(args):
    # Registry name:
    registry = get_registry(args)

    # Actual image name:
    image_name = args.kind + "-image"
    if args.image is not None:
        image_name = args.image

    # Integration image name:
    return registry + "/" + image_name
