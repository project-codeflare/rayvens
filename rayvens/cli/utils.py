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
import rayvens.cli.file as file
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


def get_integration_dockerfile(base_image,
                               input_files,
                               envvars=[],
                               with_summary=False,
                               preload_dependencies=False):
    docker_file_contents = [f"FROM {base_image}"]
    docker_file_contents.append("RUN mkdir -p /workspace")
    docker_file_contents.append("WORKDIR /workspace")

    for input_file in input_files:
        docker_file_contents.append(f"COPY {input_file} .")

    if with_summary:
        docker_file_contents.append("COPY summary.txt .")

    docker_file_contents.append("COPY config .")

    if preload_dependencies:
        # Unify input file names:
        files = " ".join(input_files)

        # Install integration in the image.
        docker_file_contents.append(f"RUN kamel local build {files} \\")
        docker_file_contents.append(
            "--integration-directory my-integration \\")
        docker_file_contents.append(
            "--dependency "
            "mvn:org.apache.camel.quarkus:camel-quarkus-java-joor-dsl \\")
        docker_file_contents.append(
            "--dependency "
            "mvn:com.googlecode.json-simple:json-simple:1.1.1 \\")
        docker_file_contents.append("--dependency "
                                    "mvn:io.kubernetes:client-java:11.0.0")
    else:
        # Overwrite the integration file with a file already filled in.
        for input_file in input_files:
            docker_file_contents.append(
                f"COPY {input_file} my-integration/routes")

    # Include any envvars that were provided.
    # The list of envvars is of the format:
    #   --env ENV_VAR=$ENV_VAR
    list_of_envars = []
    for envvar in envvars:
        list_of_envars.append(f"--env {envvar}=${envvar}")
    list_of_envars = " ".join(list_of_envars)

    docker_file_contents.append(
        "CMD kamel local run --integration-directory my-integration "
        f"{list_of_envars} "
        "--env KUBERNETES_SERVICE_PORT=${KUBERNETES_SERVICE_PORT} "
        "--env KUBERNETES_PORT=${KUBERNETES_PORT} "
        "--env HOSTNAME=${HOSTNAME} "
        "--env JAVA_VERSION=${JAVA_VERSION} "
        "--env KUBERNETES_PORT_443_TCP_ADDR=${KUBERNETES_PORT_443_TCP_ADDR} "
        "--env PATH=${PATH} "
        "--env KUBERNETES_PORT_443_TCP_PORT=$KUBERNETES_PORT_443_TCP_PORT} "
        "--env KUBERNETES_PORT_443_TCP_PROTO=${KUBERNETES_PORT_443_TCP_PROTO} "
        "--env LANG=${LANG} "
        "--env HTTP_SOURCE_ENTRYPOINT_PORT=${HTTP_SOURCE_ENTRYPOINT_PORT} "
        "--env KUBERNETES_PORT_443_TCP=${KUBERNETES_PORT_443_TCP} "
        "--env KUBERNETES_SERVICE_PORT_HTTPS=${KUBERNETES_SERVICE_PORT_HTTPS} "
        "--env LC_ALL=${LC_ALL} "
        "--env JAVA_HOME=${JAVA_HOME} "
        "--env KUBERNETES_SERVICE_HOST=${KUBERNETES_SERVICE_HOST} "
        "--env PWD=${PWD} ")
    return "\n".join(docker_file_contents)


def get_deployment_yaml(name, namespace, image_name, registry, args):
    # Kubernetes deployment options:
    replicas = 1
    full_image_name = image_name
    if registry is not None:
        full_image_name = "/".join([registry, image_name])
    image_pull_policy = "Always"
    # full_kube_proxy_image_name = get_kube_proxy_image_name(args)

    # TODO: these deployment options work with a local Kubernetes cluster
    # with a local registry i.e. localhost:5000. Test with actual cluster.

    integration_name = get_kubernetes_integration_name(name)
    entrypoint_name = get_kubernetes_entrypoint_name(name)
    label_name = get_kubernetes_label_name(name)

    container = f"""
      containers:
      - name: {image_name}
        image: {full_image_name}
        imagePullPolicy: {image_pull_policy}
"""

    with_job_launcher_priviledges = True

    job_launcher_capabilities = ""
    if (with_job_launcher_priviledges):
        job_launcher_capabilities = f"""
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {job_launcher_service_account}
  namespace: {namespace}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  namespace: {namespace}
  name: {job_manager_role}
rules:
- apiGroups: ["batch", "extensions"]
  resources: ["jobs", "jobs/status", "jobs/exec", "jobs/log"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: {job_launcher_cluster_role_binding}
subjects:
- kind: ServiceAccount
  name: {job_launcher_service_account}
  namespace: {namespace}
roleRef:
  kind: ClusterRole
  name: {job_manager_role}
  apiGroup: rbac.authorization.k8s.io
        """

        container = f"""
      serviceAccountName: {job_launcher_service_account}
""" + container

    deployment = yaml.safe_load_all(f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {integration_name}
  namespace: {namespace}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      integration: {label_name}
  template:
    metadata:
      labels:
        integration: {label_name}
    spec: {container}
---
apiVersion: v1
kind: Service
metadata:
  name: {entrypoint_name}
  namespace: {namespace}
spec:
  type: NodePort
  selector:
    integration: {label_name}
  ports:
  - port: 3000
    targetPort: 3000
    nodePort: 30001
{job_launcher_capabilities}
    """)

    # TODO: customize port.

    return deployment


def get_summary_file(args):
    integration_summary = file.SummaryFile()

    integration_summary.kind = args.kind

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


def get_process_file_contents():
    return """
import java.nio.file.Path;
import java.nio.file.Paths;
import java.io.File;

import org.apache.camel.BindToRegistry;
import org.apache.camel.Exchange;
import org.apache.camel.Processor;
import org.apache.camel.builder.RouteBuilder;
import org.apache.camel.component.aws2.s3.AWS2S3Constants;

class FileProcessor implements Processor {
    public void process(Exchange exchange) throws Exception {
        // Input is a file. Set the header entry to the file name.
        File file = exchange.getIn().getBody(File.class);
        Path path = Paths.get(file.toString());
        exchange.getIn().setHeader(AWS2S3Constants.KEY, path.getFileName());
    }
}

public class ProcessFile extends RouteBuilder {
    @BindToRegistry
    public FileProcessor processFile() {
        return new FileProcessor();
    }

    @Override
    public void configure() throws Exception {
    }
}
    """


def get_process_path_contents():
    return """
import java.nio.file.Path;
import java.nio.file.Paths;

import org.apache.camel.BindToRegistry;
import org.apache.camel.Exchange;
import org.apache.camel.Processor;
import org.apache.camel.builder.RouteBuilder;
import org.apache.camel.component.aws2.s3.AWS2S3Constants;

class PathProcessor implements Processor {
    public void process(Exchange exchange) throws Exception {
        // Input is a string with the path to the file.
        Path path = Paths.get(exchange.getIn().getBody(String.class));
        exchange.getIn().setHeader(AWS2S3Constants.KEY, path.getFileName());
        exchange.getIn().setBody(path.toFile());
    }
}

public class ProcessPath extends RouteBuilder {
    @BindToRegistry
    public PathProcessor processPath() {
        return new PathProcessor();
    }

    @Override
    public void configure() throws Exception {
    }
}
    """


def get_java_file_queue_contents():
    return """
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.io.File;
import java.io.InputStream;
import java.io.FileInputStream;

import org.apache.camel.BindToRegistry;
import org.apache.camel.Exchange;
import org.apache.camel.Processor;
import org.apache.camel.builder.RouteBuilder;

class Recv implements Processor {
    BlockingQueue<Object> queue;

    public Recv(BlockingQueue<Object> queue) {
        this.queue = queue;
    }

    public void process(Exchange exchange) throws Exception {
        File file = exchange.getIn().getBody(File.class);
        long fileSize = file.length();

        // TODO: find a better way to read the file content.
        byte[] allBytes = new byte[(int) fileSize];
        InputStream inputStream = new FileInputStream(file);
        inputStream.read(allBytes);
        inputStream.close();
        queue.add(allBytes);
    }
}

class Send implements Processor {
    BlockingQueue<Object> queue;

    public Send(BlockingQueue<Object> queue) {
        this.queue = queue;
    }

    public void process(Exchange exchange) throws Exception {
        Object body = queue.take();
        exchange.getIn().setBody(body);
    }
}
    """


def get_java_file_queue_json_contents():
    return """
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.io.File;

import org.apache.camel.BindToRegistry;
import org.apache.camel.Exchange;
import org.apache.camel.Processor;
import org.apache.camel.builder.RouteBuilder;
import org.json.simple.JSONObject;

class Recv implements Processor {
    BlockingQueue<Object> queue;

    public Recv(BlockingQueue<Object> queue) {
        this.queue = queue;
    }

    public void process(Exchange exchange) throws Exception {
        JSONObject returnJsonObject = new JSONObject();
        String body = exchange.getIn().getBody(String.class);
        returnJsonObject.put("body", body);

        Object key = exchange.getIn().getHeader("CamelAwsS3Key");
        returnJsonObject.put("filename", key.toString());
        queue.add(returnJsonObject.toString());
    }
}

class Send implements Processor {
    BlockingQueue<Object> queue;

    public Send(BlockingQueue<Object> queue) {
        this.queue = queue;
    }

    public void process(Exchange exchange) throws Exception {
        Object body = queue.take();
        exchange.getIn().setBody(body);
    }
}

public class FileQueueJson extends RouteBuilder {
    BlockingQueue<Object> queue = new LinkedBlockingQueue<Object>();

    @BindToRegistry
    public Recv addToFileJsonQueue() {
        return new Recv(queue);
    }

    @BindToRegistry
    public Send takeFromFileJsonQueue() {
        return new Send(queue);
    }

    @Override
    public void configure() throws Exception {
    }
}
    """


def get_java_file_watch_queue_contents():
    return """
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.io.File;
import java.io.InputStream;
import java.io.FileInputStream;

import org.apache.camel.BindToRegistry;
import org.apache.camel.Exchange;
import org.apache.camel.Processor;
import org.apache.camel.builder.RouteBuilder;
import org.json.simple.JSONObject;

class Recv implements Processor {
    BlockingQueue<Object> queue;

    public Recv(BlockingQueue<Object> queue) {
        this.queue = queue;
    }

    public void process(Exchange exchange) throws Exception {
        JSONObject returnJsonObject = new JSONObject();

        // Record event type:
        Object eventType = exchange.getIn().getHeader("CamelFileEventType");
        returnJsonObject.put("event_type", eventType.toString());

        // Record event type:
        File file = exchange.getIn().getBody(File.class);
        returnJsonObject.put("filename", file.toString());
        queue.add(returnJsonObject.toString());
    }
}

class Send implements Processor {
    BlockingQueue<Object> queue;

    public Send(BlockingQueue<Object> queue) {
        this.queue = queue;
    }

    public void process(Exchange exchange) throws Exception {
        Object body = queue.take();
        exchange.getIn().setBody(body);
    }
}

public class FileWatchQueue extends RouteBuilder {
    BlockingQueue<Object> queue = new LinkedBlockingQueue<Object>();

    @BindToRegistry
    public Recv addToFileWatchQueue() {
        return new Recv(queue);
    }

    @BindToRegistry
    public Send takeFromFileWatchQueue() {
        return new Send(queue);
    }

    @Override
    public void configure() throws Exception {
    }
}
    """


def get_java_meta_event_queue_contents():
    return """
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.io.File;
import java.io.InputStream;
import java.io.FileInputStream;

import org.apache.camel.BindToRegistry;
import org.apache.camel.Exchange;
import org.apache.camel.Processor;
import org.apache.camel.builder.RouteBuilder;
import org.json.simple.JSONObject;

class Recv implements Processor {
    BlockingQueue<Object> queue;

    public Recv(BlockingQueue<Object> queue) {
        this.queue = queue;
    }

    public void process(Exchange exchange) throws Exception {
        JSONObject returnJsonObject = new JSONObject();
        Object key = exchange.getIn().getHeader("CamelAwsS3Key");
        returnJsonObject.put("filename", key.toString());
        queue.add(returnJsonObject.toString());
    }
}

class Send implements Processor {
    BlockingQueue<Object> queue;

    public Send(BlockingQueue<Object> queue) {
        this.queue = queue;
    }

    public void process(Exchange exchange) throws Exception {
        Object body = queue.take();
        exchange.getIn().setBody(body);
    }
}

public class MetaEventQueue extends RouteBuilder {
    BlockingQueue<Object> queue = new LinkedBlockingQueue<Object>();

    @BindToRegistry
    public Recv addToMetaEventQueue() {
        return new Recv(queue);
    }

    @BindToRegistry
    public Send takeFromMetaEventQueue() {
        return new Send(queue);
    }

    @Override
    public void configure() throws Exception {
    }
}
    """


def get_java_queue_contents(job_command="[env]"):
    job_spec = f"""
        eventContents = eventContents.replace("\\\"", "");
        String newLine = System.getProperty("line.separator");
        String finalString = "apiVersion: batch/v1" + newLine
             + "kind: Job" + newLine
             + "metadata:" + newLine
             + "  name: "+ jobName + newLine
             + "spec:" + newLine
             + "  template:" + newLine
             + "    spec:" + newLine
             + "      containers:" + newLine
             + "      - name: " + jobName + "-container" + newLine
             + "        image: adoptopenjdk/openjdk11:alpine" + newLine
             + "        env:" + newLine
             + "        - name: TEST_EVENT" + newLine
             + "          value: \\\"" + eventContents + "\\\"" + newLine
             + "        command: {job_command}" + newLine
             + "      restartPolicy: Never" + newLine
             + "  backoffLimit: 4" + newLine;
        System.out.println(finalString);
        return finalString;
    """

    java_queue_file = """
import java.lang.Runnable;
import java.lang.Thread;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;

import org.apache.camel.BindToRegistry;
import org.apache.camel.Exchange;
import org.apache.camel.Processor;
import org.apache.camel.builder.RouteBuilder;

import java.lang.ProcessBuilder;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.File;
import java.io.FileWriter;
import java.util.function.Consumer;
import java.util.concurrent.Executors;
import java.lang.Runtime;
import java.lang.Process;

import java.io.IOException;
import com.google.gson.Gson;
import io.kubernetes.client.openapi.ApiClient;
import io.kubernetes.client.openapi.ApiException;
import io.kubernetes.client.openapi.apis.BatchV1Api;
import io.kubernetes.client.openapi.models.V1Job;
import io.kubernetes.client.util.Config;
import java.util.Map;
import org.yaml.snakeyaml.Yaml;
import org.yaml.snakeyaml.constructor.SafeConstructor;

class HelloRunnable implements Runnable {
    String body;
    int eventCount;

    public HelloRunnable(String body, int eventCount) {
        super();
        this.body = body;
        this.eventCount = eventCount;
    }

    public String getJobYaml(String jobName, String eventContents) {
        %s
    }

    public void createYamlFile(String filename) {
        try {
            File file = new File(filename);
            if (file.createNewFile()) {
                System.out.println("Yaml file created: " + file.getName());
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public void writeJobYamlFile(String filename, String contents) {
        createYamlFile(filename);
        try {
            FileWriter myWriter = new FileWriter(filename);
            myWriter.write(contents);
            myWriter.close();
            System.out.println("Successfully wrote yaml file.");
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public void deleteYamlFile(String filename) {
        File file = new File(filename);
        if (file.delete()) {
            System.out.println("Deleted the yaml file: " + file.getName());
        } else {
            System.out.println("Failed to delete the yaml file.");
        }
    }

    private static class StreamConsumer implements Runnable {
        private InputStream inputStream;
        private Consumer<String> consumer;

        public StreamConsumer(InputStream inputStream,
                              Consumer<String> consumer) {
            this.inputStream = inputStream;
            this.consumer = consumer;
        }

        @Override
        public void run() {
            new BufferedReader(new InputStreamReader(inputStream)).lines()
              .forEach(consumer);
        }
    }

    public void run() {
        System.out.println("Hello from a thread!");
        System.out.println(this.body);

        ProcessBuilder builder = new ProcessBuilder();
        String filename = "temp-job-"+String.valueOf(this.eventCount)+".yaml";
        String jobName = "random-job-name-"+String.valueOf(this.eventCount);
        writeJobYamlFile(filename, getJobYaml(jobName, this.body));
        builder.command("bash", "-c", "kubectl apply -f "+filename);

        try {
            Process process = builder.start();
            StreamConsumer outStream = new StreamConsumer(
                process.getInputStream(), System.out::println);
            Executors.newSingleThreadExecutor().submit(outStream);
            StreamConsumer errStream = new StreamConsumer(
                process.getErrorStream(), System.out::println);
            Executors.newSingleThreadExecutor().submit(errStream);
            try {
                int exitCode = process.waitFor();
                assert exitCode == 0;
            } catch (InterruptedException e) {
                System.err.println("Exception when calling process.waitFor()");
                e.printStackTrace();
            }
        } catch (IOException e) {
            System.err.println("Exception when calling builder.start()");
            e.printStackTrace();
        }

        deleteYamlFile(filename);
    }
}

class Recv implements Processor {
    BlockingQueue<Object> queue;
    int eventCount;

    public Recv(BlockingQueue<Object> queue) {
        this.queue = queue;
        this.eventCount = 0;
    }

    public void process(Exchange exchange) throws Exception {
        String body = exchange.getIn().getBody(String.class);
        queue.add(body);
        this.eventCount += 1;
        (new Thread(new HelloRunnable(body, this.eventCount))).start();
    }
}

class Send implements Processor {
    BlockingQueue<Object> queue;

    public Send(BlockingQueue<Object> queue) {
        this.queue = queue;
    }

    public void process(Exchange exchange) throws Exception {
        Object body = queue.take();
        exchange.getIn().setBody(body);
    }
}

public class Queue extends RouteBuilder {
    BlockingQueue<Object> queue = new LinkedBlockingQueue<Object>();

    @BindToRegistry
    public Recv addToQueue() {
        return new Recv(queue);
    }

    @BindToRegistry
    public Send takeFromQueue() {
        return new Send(queue);
    }

    @Override
    public void configure() throws Exception {
    }
}
    """ % (job_spec)

    return java_queue_file


def _create_file(workspace_directory, file_name, file_contents):
    file_processor_file_path = workspace_directory.joinpath(file_name)
    with open(file_processor_file_path, 'w') as f:
        f.write(file_contents)
    return file_name


# REMOVE
def add_additional_files(workspace_directory, predefined_integration, spec,
                         inverted_transport):
    files = []
    if catalog_utils.integration_requires_file_processor(spec):
        files.append(
            _create_file(workspace_directory, "ProcessFile.java",
                         get_process_file_contents()))

    if catalog_utils.integration_requires_path_processor(spec):
        files.append(
            _create_file(workspace_directory, "ProcessPath.java",
                         get_process_path_contents()))

    # Write the Java queue code to the file when using HTTP transport.
    if inverted_transport:
        if catalog_utils.integration_requires_file_queue(spec):
            files.append(
                _create_file(workspace_directory, "FileQueue.java",
                             get_java_file_queue_contents()))

        if catalog_utils.integration_requires_file_queue(spec):
            files.append(
                _create_file(workspace_directory, "FileQueueJson.java",
                             get_java_file_queue_json_contents()))

        if catalog_utils.integration_requires_file_watch_queue(spec):
            files.append(
                _create_file(workspace_directory, "FileWatchQueue.java",
                             get_java_file_watch_queue_contents()))

        if catalog_utils.integration_requires_meta_event_queue(spec):
            files.append(
                _create_file(workspace_directory, "MetaEventQueue.java",
                             get_java_meta_event_queue_contents()))

        if catalog_utils.integration_requires_queue(spec):
            files.append(
                _create_file(workspace_directory, "Queue.java",
                             get_java_queue_contents()))
    return files


def get_additional_files(spec, inverted_transport):
    files = []
    if catalog_utils.integration_requires_file_processor(spec):
        files.append(
            file.File("ProcessFile.java",
                      contents=get_process_file_contents()))

    if catalog_utils.integration_requires_path_processor(spec):
        files.append(
            file.File("ProcessPath.java",
                      contents=get_process_path_contents()))

    # Write the Java queue code to the file when using HTTP transport.
    if inverted_transport:
        if catalog_utils.integration_requires_file_queue(spec):
            files.append(
                file.File("FileQueue.java",
                          contents=get_java_file_queue_contents()))

        if catalog_utils.integration_requires_file_queue(spec):
            files.append(
                file.File("FileQueueJson.java",
                          contents=get_java_file_queue_json_contents()))

        if catalog_utils.integration_requires_file_watch_queue(spec):
            files.append(
                file.File("FileWatchQueue.java",
                          contents=get_java_file_watch_queue_contents()))

        if catalog_utils.integration_requires_meta_event_queue(spec):
            files.append(
                file.File("MetaEventQueue.java",
                          contents=get_java_meta_event_queue_contents()))

        if catalog_utils.integration_requires_queue(spec):
            files.append(
                file.File("Queue.java", contents=get_java_queue_contents()))
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


def clean_error_exit(workspace_directory, message):
    file.delete_workspace_directory(workspace_directory)
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
    config, _ = fill_config(kind, properties, show_missing=False)
    return config


def get_modeline_header_code(args):
    # Get the kind of the integration:
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

    # Transform configuarion in list of modeline properties:
    modeline_properties = get_modeline_properties(kind, envvars)
    result = []
    for key in modeline_properties:
        result.append(modeline_properties[key])
    return "\n".join(result)


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

    # Transform configuarion in list of modeline properties:
    modeline_properties = get_modeline_properties(kind, envvars)
    result = []
    for key in modeline_properties:
        result.append(modeline_properties[key])
    return result


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


def get_kube_proxy_image_name(args):
    # Registry name:
    registry = get_registry(args)

    # Base image name:
    return registry + "/" + kube_proxy_image_name
