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
from rayvens.core.catalog_utils import get_current_config, get_all_properties
from rayvens.core.catalog_utils import fill_config

base_image_name = "integration-base"


def get_integration_dockerfile(base_image,
                               integration_file_name,
                               with_summary=False,
                               preload_dependencies=False):
    docker_file_contents = [f"FROM {base_image}"]
    docker_file_contents.append("RUN mkdir -p /workspace")
    docker_file_contents.append("WORKDIR /workspace")

    docker_file_contents.append(f"COPY {integration_file_name} .")

    if with_summary:
        docker_file_contents.append("COPY summary.txt .")

    if preload_dependencies:
        docker_file_contents.append(
            f"RUN kamel local inspect {integration_file_name} \\")
        docker_file_contents.append(
            "--dependency "
            "mvn:org.apache.camel.quarkus:camel-quarkus-java-joor-dsl")
    docker_file_contents.append(
        f"CMD kamel local run {integration_file_name} \\")
    docker_file_contents.append(
        "--dependency mvn:org.apache.camel.quarkus:camel-quarkus-java-joor-dsl"
    )
    return "\n".join(docker_file_contents)


def get_summary_file_contents(args):
    summary = []

    summary.append(f"kind={args.kind}")

    base_config, missing_property_value = get_current_config(args)
    for property_key in base_config:
        if property_key not in missing_property_value:
            summary.append(f"{property_key}={base_config[property_key]}")

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
    for property_value in args.properties:
        components = property_value.split("=")
        given_properties.append(components[0])
    return given_properties


def check_properties(kind, properties):
    invalid_props = []
    valid_properties = get_all_properties(kind)
    for property_name in properties:
        if property_name not in valid_properties:
            invalid_props.append(property_name)
    return invalid_props


def summary_file_path(workspace_directory):
    return workspace_directory.joinpath("summary.txt")


def _get_field_from_summary(summary_file_path, field):
    result = None
    with open(summary_file_path, "r") as summary:
        for line in summary.readlines():
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


def summary_get_properties(kind, workspace_directory):
    properties = []
    summary_path = summary_file_path(workspace_directory)
    valid_properties = get_all_properties(kind)
    for property_name in valid_properties:
        property_value = _get_field_from_summary(summary_path, property_name)
        if property_value is not None:
            properties.append(f"{property_name}={property_value}")
    return properties


def get_full_config(workspace_directory, args):
    # Get the kind of the integration:
    kind = summary_get_kind(workspace_directory)

    # Get summary values that are not in the current set of args:
    given_properties = get_given_properties(args)

    # Validate user-given properties:
    invalid_props = check_properties(kind, given_properties)
    if len(invalid_props) > 0:
        invalid_props = " ".join(invalid_props)
        clean_error_exit(workspace_directory,
                         f"Invalid properties provided: {invalid_props}")

    # Assemble list of all property-value pairs:
    properties = args.properties
    properties.extend(summary_get_properties(kind, workspace_directory))

    # Fill configuration with values:
    config, _ = fill_config(kind, properties)
    return config
