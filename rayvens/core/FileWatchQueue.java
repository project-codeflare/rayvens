/*
 * Copyright IBM Corporation 2021
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

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
