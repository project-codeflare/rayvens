import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.UnsupportedEncodingException;
import java.net.ServerSocket;
import java.net.Socket;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;

import org.apache.camel.BindToRegistry;
import org.apache.camel.Exchange;
import org.apache.camel.Processor;
import org.apache.camel.builder.RouteBuilder;

class Recv implements Processor {
    BlockingQueue<String> queue;

    public Recv(BlockingQueue<String> queue) {
        this.queue = queue;
    }

    public void process(Exchange exchange) throws Exception {
        String body = exchange.getIn().getBody(String.class);
        queue.add(body);
    }
}

class Send implements Processor {
    BlockingQueue<String> queue;

    public Send(BlockingQueue<String> queue) {
        this.queue = queue;
    }

    public void process(Exchange exchange) throws Exception {
        String body = queue.take();
        exchange.getIn().setBody(body);
    }
}

public class Queue extends RouteBuilder {
    BlockingQueue<String> queue = new LinkedBlockingQueue<String>();

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
