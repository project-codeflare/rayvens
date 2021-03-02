import ray


@ray.remote
class EventTopic(object):
    def __init__(self, name):
        self.name = name
        self.subscribers = []

    def subscribe(self, subscriberFunction):
        self.subscribers.append(subscriberFunction)

    def publish(self, *args, **kwargs):
        for subscriberFunction in self.subscribers:
            subscriberFunction(*args, **kwargs)

    def publishToRemote(self, *args, **kwargs):
        for subscriberFunction in self.subscribers:
            subscriberFunction.remote(*args, **kwargs)

    def describe(self):
        print("Topic name:", self.name)
        print("Number of subscribers:", len(self.subscribers))
