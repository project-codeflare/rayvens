import ray
import rayvens

try:
    ray.init(address='auto')
except ConnectionError:
    ray.init(object_store_memory=78643200)

client = rayvens.Client()

topic = client.create_topic('example')


def handler1(event):
    print('handler1 received', event)


def handler2(event):
    print('handler2 received', event)


topic >> handler1
topic >> handler2

for i in range(10):
    topic << f'event {i}'
