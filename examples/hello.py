import ray
import rayvens

ray.init()
client = rayvens.Client()

stream = client.create_stream('example')

stream >> print

stream << 'hello' << 'world'
