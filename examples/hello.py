import ray
import rayvens

ray.init()
client = rayvens.Client()

topic = client.create_topic('example')

topic >> print

topic << 'hello' << 'world'
