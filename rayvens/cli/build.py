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
import yaml
import rayvens.cli.utils as utils
from rayvens.core.catalog import sources, sinks
from rayvens.core.catalog import construct_source, construct_sink
from rayvens.cli.docker import docker_push, docker_build


def build_base_image(args):
    # Create a work directory in the current directory:
    workspace_directory = pathlib.Path.cwd().joinpath("workspace")
    os.mkdir(workspace_directory)

    # Write preloader contents:
    preloader_file_contents = """
import org.apache.camel.BindToRegistry;
import org.apache.camel.Exchange;
import org.apache.camel.Processor;
import org.apache.camel.builder.RouteBuilder;

class Exit implements Processor {
  public void process(Exchange exchange) throws Exception {
    System.exit(0);
  }
}

public class Preloader extends RouteBuilder {
  @Override
  public void configure() throws Exception {
    from("timer:tick").to("bean:exit");
    from("platform-http:/null").to("http:null");
  }

  @BindToRegistry
  public Exit exit() {
    return new Exit();
  }
}
"""

    preloader_file_path = workspace_directory.joinpath("Preloader.java")
    with open(preloader_file_path, mode='w') as preloader_file:
        preloader_file.write(preloader_file_contents)

    # Copy the current kamel executable in the workspace directory:
    path_to_kamel = utils.find_executable("kamel")
    print("path_to_kamel=", path_to_kamel)
    print("dest=", str(workspace_directory.joinpath("kamel")))
    utils.copy_file(path_to_kamel, str(workspace_directory.joinpath("kamel")))

    # Write docker file contents
    docker_file_contents = """
FROM adoptopenjdk/openjdk11:alpine

RUN apk add --update maven && apk update && apk upgrade

COPY --from=docker.io/apache/camel-k:1.5.0 /usr/local/bin/kamel /usr/local/bin/
COPY kamel /usr/local/bin/

COPY Preloader.java .
RUN kamel local run Preloader.java \
    --dependency mvn:org.apache.camel.quarkus:camel-quarkus-java-joor-dsl; \
    rm Preloader.java
"""

    docker_file_path = workspace_directory.joinpath("Dockerfile")
    with open(docker_file_path, mode='w') as docker_file:
        docker_file.write(docker_file_contents)

    # Base image name:
    base_image_name = get_base_image_name(args)

    # Build base image:
    #   docker build workspace -t <image>
    docker_build(str(workspace_directory), base_image_name)

    # Push base image to registry:
    #   docker push <image>
    docker_push(base_image_name)

    # Make the directory empty:
    for file in workspace_directory.iterdir():
        os.remove(file)

    # Delete the empty directory:
    os.rmdir(workspace_directory)


def build_integration(args):
    # Create a work directory in the current directory:
    workspace_directory = pathlib.Path.cwd().joinpath("workspace")
    os.mkdir(workspace_directory)

    # Check if the source/sink is predefined.
    predefined_integration = args.kind is not None and (args.kind in sources
                                                        or args.kind in sinks)
    # By default the HTTP transport is used. This is the only supported
    # transport for now.
    inverted_transport = True

    # Put together the specification file.
    integration_file_path = None
    integration_file_name = None
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
        integration_file_path = workspace_directory.joinpath(
            integration_file_name)
        with open(integration_file_path, 'w') as f:
            modeline_options = utils.get_modeline_config(workspace_directory,
                                                         args,
                                                         run=False)
            f.write("\n".join(modeline_options) + "\n\n")
            f.write(yaml.dump(spec))

        # Put together the summary file.
        summary_file_contents = utils.get_summary_file_contents(args)
        print("Summary file contents:")
        print(summary_file_contents)
        summary_file_name = 'summary.txt'
        summary_file_path = workspace_directory.joinpath(summary_file_name)
        with open(summary_file_path, 'w') as summary_file:
            summary_file.write(summary_file_contents)
    else:
        raise utils.clean_error_exit(workspace_directory,
                                     "Not implemented yet")

    # Resolve base image name:
    base_image = get_base_image_name(args)

    # Write docker file contents:
    envvars = utils.get_modeline_envvars(workspace_directory, args)
    docker_file_contents = utils.get_integration_dockerfile(
        base_image,
        integration_file_name,
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

    # Make the directory empty:
    for file in workspace_directory.iterdir():
        os.remove(file)

    # Delete the empty directory:
    os.rmdir(workspace_directory)


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
