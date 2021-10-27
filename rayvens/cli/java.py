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

# The preloader file is fixed and can just be a string.
preloader_file_name = "Preloader.java"
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


def get_job_launcher(launch_image):
    if launch_image is None:
        return ""

    job_command = "[env]"
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
             + "        image: {launch_image}" + newLine
             + "        env:" + newLine
             + "        - name: TEST_EVENT" + newLine
             + "          value: \\\"" + eventContents + "\\\"" + newLine
             + "        command: {job_command}" + newLine
             + "      restartPolicy: Never" + newLine
             + "  backoffLimit: 4" + newLine;
        System.out.println(finalString);
        return finalString;
    """

    job_launcher = """
import java.lang.Runnable;
import java.lang.Thread;

import java.lang.ProcessBuilder;
import java.io.BufferedReader;

import java.io.InputStreamReader;
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

class YamlRunnable implements Runnable {
    String body;
    int eventCount;

    public YamlRunnable(String body, int eventCount) {
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
    """ % (job_spec)
    return job_launcher


def get_queue_management_code(job_launcher, receive_processor, send_processor,
                              class_name, recv_method_name, send_method_name):
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

%s

class Recv implements Processor {
    BlockingQueue<Object> queue;
    int eventCount;

    public Recv(BlockingQueue<Object> queue) {
        this.queue = queue;
        this.eventCount = 0;
    }

    %s
}

class Send implements Processor {
    BlockingQueue<Object> queue;

    public Send(BlockingQueue<Object> queue) {
        this.queue = queue;
    }

    %s
}

public class %s extends RouteBuilder {
    BlockingQueue<Object> queue = new LinkedBlockingQueue<Object>();

    @BindToRegistry
    public Recv %s() {
        return new Recv(queue);
    }

    @BindToRegistry
    public Send %s() {
        return new Send(queue);
    }

    @Override
    public void configure() throws Exception {
    }
}
    """ % (job_launcher, receive_processor, send_processor, class_name,
           recv_method_name, send_method_name)


def job_launched_and_handler(launch_image):
    job_launcher = get_job_launcher(launch_image)
    handle_event_content = """
        queue.add(body);
    """
    if launch_image is not None:
        handle_event_content = """
        this.eventCount += 1;
        (new Thread(new YamlRunnable(body, this.eventCount))).start();
        """
    return job_launcher, handle_event_content


def get_java_file_queue_contents(launch_image):
    job_launcher, handle_event_content = job_launched_and_handler(launch_image)
    receive_processor = """
    public void process(Exchange exchange) throws Exception {
        File file = exchange.getIn().getBody(File.class);
        long fileSize = file.length();

        // TODO: find a better way to read the file content.
        byte[] allBytes = new byte[(int) fileSize];
        InputStream inputStream = new FileInputStream(file);
        inputStream.read(allBytes);
        inputStream.close();
        String body = new String(allBytes, StandardCharsets.UTF_8);
        %s
    }
    """ % (handle_event_content)

    send_processor = """
    public void process(Exchange exchange) throws Exception {
        Object body = queue.take();
        exchange.getIn().setBody(body);
    }
    """

    class_name = "FileQueue"
    recv_method_name = "addToFileQueue"
    send_method_name = "takeFromFileQueue"
    return get_queue_management_code(job_launcher, receive_processor,
                                     send_processor, class_name,
                                     recv_method_name, send_method_name)


def get_java_file_queue_json_contents(launch_image):
    job_launcher, handle_event_content = job_launched_and_handler(launch_image)
    receive_processor = """
    public void process(Exchange exchange) throws Exception {
        JSONObject returnJsonObject = new JSONObject();
        String body = exchange.getIn().getBody(String.class);
        returnJsonObject.put("body", body);

        Object key = exchange.getIn().getHeader("CamelAwsS3Key");
        returnJsonObject.put("filename", key.toString());
        String body = returnJsonObject.toString();
        %s
    }
    """ % (handle_event_content)

    send_processor = """
    public void process(Exchange exchange) throws Exception {
        Object body = queue.take();
        exchange.getIn().setBody(body);
    }
    """

    class_name = "FileQueueJson"
    recv_method_name = "addToFileJsonQueue"
    send_method_name = "takeFromFileJsonQueue"
    return get_queue_management_code(job_launcher, receive_processor,
                                     send_processor, class_name,
                                     recv_method_name, send_method_name)


def get_java_file_watch_queue_contents(launch_image):
    job_launcher, handle_event_content = job_launched_and_handler(launch_image)
    receive_processor = """
    public void process(Exchange exchange) throws Exception {
        JSONObject returnJsonObject = new JSONObject();

        // Record event type:
        Object eventType = exchange.getIn().getHeader("CamelFileEventType");
        returnJsonObject.put("event_type", eventType.toString());

        // Record event type:
        File file = exchange.getIn().getBody(File.class);
        returnJsonObject.put("filename", file.toString());
        String body = returnJsonObject.toString();
        %s
    }
    """ % (handle_event_content)

    send_processor = """
    public void process(Exchange exchange) throws Exception {
        Object body = queue.take();
        exchange.getIn().setBody(body);
    }
    """

    class_name = "FileWatchQueue"
    recv_method_name = "addToFileWatchQueue"
    send_method_name = "takeFromFileWatchQueue"
    return get_queue_management_code(job_launcher, receive_processor,
                                     send_processor, class_name,
                                     recv_method_name, send_method_name)


def get_java_meta_event_queue_contents(launch_image):
    job_launcher, handle_event_content = job_launched_and_handler(launch_image)
    receive_processor = """
    public void process(Exchange exchange) throws Exception {
        JSONObject returnJsonObject = new JSONObject();
        Object key = exchange.getIn().getHeader("CamelAwsS3Key");
        returnJsonObject.put("filename", key.toString());
        String body = returnJsonObject.toString();
        %s
    }
    """ % (handle_event_content)

    send_processor = """
    public void process(Exchange exchange) throws Exception {
        Object body = queue.take();
        exchange.getIn().setBody(body);
    }
    """

    class_name = "MetaEventQueue"
    recv_method_name = "addToMetaEventQueue"
    send_method_name = "takeFromMetaEventQueue"
    return get_queue_management_code(job_launcher, receive_processor,
                                     send_processor, class_name,
                                     recv_method_name, send_method_name)


def get_java_queue_contents(launch_image):
    job_launcher, handle_event_content = job_launched_and_handler(launch_image)
    receive_processor = """
    public void process(Exchange exchange) throws Exception {
        String body = exchange.getIn().getBody(String.class);
        %s
    }
    """ % (handle_event_content)

    send_processor = """
    public void process(Exchange exchange) throws Exception {
        Object body = queue.take();
        exchange.getIn().setBody(body);
    }
    """

    class_name = "Queue"
    recv_method_name = "addToQueue"
    send_method_name = "takeFromQueue"
    java_queue_file = get_queue_management_code(job_launcher,
                                                receive_processor,
                                                send_processor, class_name,
                                                recv_method_name,
                                                send_method_name)
    return java_queue_file
