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

import java.nio.file.Path;
import java.nio.file.Paths;

import org.apache.camel.BindToRegistry;
import org.apache.camel.Exchange;
import org.apache.camel.Processor;
import org.apache.camel.builder.RouteBuilder;
import org.apache.camel.component.aws2.s3.AWS2S3Constants;

class FileProcessor implements Processor {
    public void process(Exchange exchange) throws Exception {
        Path path = Paths.get(exchange.getIn().getBody(String.class));
        exchange.getIn().setHeader(AWS2S3Constants.KEY, path.getFileName());
        exchange.getIn().setBody(path.toFile());
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
