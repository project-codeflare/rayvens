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
import subprocess
import platform
from rayvens.core.catalog_utils import get_all_properties
from rayvens.core.catalog_utils import integration_requirements
from rayvens.core.catalog_utils import get_modeline_properties
from rayvens.core.catalog_utils import fill_config

base_image_name = "integration-base"
property_prefix = "property: "
envvar_prefix = "envvar: "


def get_integration_dockerfile(base_image,
                               integration_file_name,
                               envvars=[],
                               with_summary=False,
                               preload_dependencies=False):
    docker_file_contents = [f"FROM {base_image}"]
    docker_file_contents.append("RUN mkdir -p /workspace")
    docker_file_contents.append("WORKDIR /workspace")

    docker_file_contents.append(f"COPY {integration_file_name} .")

    if with_summary:
        docker_file_contents.append("COPY summary.txt .")

    if preload_dependencies:
        # Install integration in the image.
        docker_file_contents.append(
            f"RUN kamel local build {integration_file_name} \\")
        docker_file_contents.append(
            "--integration-directory my-integration \\")
        docker_file_contents.append(
            "--dependency "
            "mvn:org.apache.camel.quarkus:camel-quarkus-java-joor-dsl")
    else:
        # Overwrite the integration file with a file already filled in.
        docker_file_contents.append(
            f"COPY {integration_file_name} my-integration/routes")

    # Include any envvars that were provided.
    # The list of envvars is of the format:
    #   --env ENV_VAR=$ENV_VAR
    list_of_envars = []
    for envvar in envvars:
        list_of_envars.append(f"--env {envvar}=${envvar}")
    list_of_envars = " ".join(list_of_envars)

    docker_file_contents.append(
        "CMD kamel local run --integration-directory my-integration "
        f"{list_of_envars}")
    return "\n".join(docker_file_contents)


def get_summary_file_contents(args):
    summary = []

    summary.append(f"kind={args.kind}")

    if args.properties is not None:
        config, missing_property_value = fill_config(args.kind,
                                                     args.properties,
                                                     show_missing=False)
        for key in config:
            if key not in missing_property_value:
                summary.append(f"{property_prefix}{key}={config[key]}")

    envvars = get_current_envvars(args)
    for property_key in envvars:
        summary.append(
            f"{envvar_prefix}{property_key}={envvars[property_key]}")

    return "\n".join(summary)


def get_registry(args):
    # Registry name:
    registry = None
    if args.dev is not None:
        registry = "localhost:5000"
    else:
        raise RuntimeError(
            "the --dev flag is required for `rayvens base` call")

    return registry


def create_workspace_dir():
    workspace_directory = pathlib.Path.cwd().joinpath("workspace")
    os.mkdir(workspace_directory)
    return workspace_directory


def delete_workspace_dir(workspace_directory):
    # Make the directory empty:
    for file in workspace_directory.iterdir():
        os.remove(file)

    # Delete the empty directory:
    os.rmdir(workspace_directory)


def clean_error_exit(workspace_directory, message):
    delete_workspace_dir(workspace_directory)
    raise RuntimeError(message)


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
            given_envvars.append(components[1])
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
                result = components[1]
                break

    if result is None:
        return None

    return result.strip()


def summary_get_kind(workspace_directory):
    summary_path = summary_file_path(workspace_directory)
    return _get_field_from_summary(summary_path, "kind")


def summary_get_envvar_properties(kind, workspace_directory, given_envvars):
    envvars = []
    summary_path = summary_file_path(workspace_directory)
    valid_properties = get_all_properties(kind)
    for property_name in valid_properties:
        if property_name not in given_envvars:
            property_value = _get_field_from_summary(summary_path,
                                                     property_name,
                                                     prefix=envvar_prefix)
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


def summary_get_properties(kind, workspace_directory, given_properties):
    properties = []
    summary_path = summary_file_path(workspace_directory)
    valid_properties = get_all_properties(kind)
    for property_name in valid_properties:
        if property_name not in given_properties:
            property_value = _get_field_from_summary(summary_path,
                                                     property_name,
                                                     prefix=property_prefix)
            if property_value is not None:
                properties.append(f"{property_name}={property_value}")
    return properties


def get_current_envvars(args):
    envvars = {}
    if args.envvars is not None and len(args.envvars) > 0:
        for property_env_pair in args.envvars:
            components = property_env_pair.split("=")
            envvars[components[0]] = components[1]
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
            config[components[0]] = components[1]

    if len(requirements['required']) > 0:
        for req_property in requirements['required']:
            if req_property not in config:
                missing_requirements.append(req_property)
                config[req_property] = "missing_property_value"

    return config, missing_requirements


def get_full_config(workspace_directory, args):
    # Get the kind of the integration:
    kind = summary_get_kind(workspace_directory)

    # Get properties given as args:
    given_properties = get_given_properties(args)

    # Validate user-given properties:
    invalid_props = check_properties(kind, given_properties)
    if len(invalid_props) > 0:
        invalid_props = " ".join(invalid_props)
        clean_error_exit(workspace_directory,
                         f"Invalid properties provided: {invalid_props}")

    # Assemble list of all property-value pairs:
    properties = []
    if args.properties is not None:
        properties = args.properties
    properties.extend(
        summary_get_properties(kind, workspace_directory, given_properties))

    # Fill configuration with values:
    config, _ = fill_config(kind, properties)
    return config


def get_modeline_config(workspace_directory, args, run=True):
    # Get the kind of the integration:
    if run:
        kind = summary_get_kind(workspace_directory)
    else:
        kind = args.kind

    # Get envvars given as args:
    given_envvars = get_given_property_envvars(args)

    # Validate user-given envvars:
    invalid_props = check_properties(kind, given_envvars)
    if len(invalid_props) > 0:
        invalid_props = " ".join(invalid_props)
        clean_error_exit(workspace_directory,
                         f"Invalid properties provided: {invalid_props}")

    # Assemble list of all property-value envvar pairs:
    envvars = []
    if args.envvars is not None:
        envvars = args.envvars
    if run:
        envvars.extend(
            summary_get_envvar_properties(kind, workspace_directory,
                                          given_envvars))

    print("Modeline config:")
    print(envvars)

    # Transform configuarion in list of modeline properties:
    modeline_properties = get_modeline_properties(kind, envvars)
    result = []
    for key in modeline_properties:
        result.append(modeline_properties[key])
    return result


def get_modeline_envvars(workspace_directory, args):
    # Get the kind of the integration:
    kind = summary_get_kind(workspace_directory)

    # Get envvars given as args:
    given_envvars = get_given_envvars(args)

    # Get envvars from summary file:
    given_envvars.extend(summary_get_envvars(kind, workspace_directory))
    return given_envvars


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
