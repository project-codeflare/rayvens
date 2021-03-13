import ray
import rayvens

ray.init()
client = rayvens.Client()

stream = client.create_stream('example')

# deliver all events to print
stream >> print

# append two events to the stream
stream << 'hello' << 'world'
