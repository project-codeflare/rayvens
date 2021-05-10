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
