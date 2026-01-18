import time
import threading
from collections import defaultdict

class Message:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    
    def __repr__(self):
        return str(self.__dict__)

class Bus:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Bus, cls).__new__(cls)
            cls._instance.topics = defaultdict(list)
            cls._instance.last_messages = {}
        return cls._instance

    def publish(self, topic, message):
        self.last_messages[topic] = message
        for callback in self.topics[topic]:
            callback(message)

    def subscribe(self, topic, callback):
        self.topics[topic].append(callback)

    def get_last_message(self, topic):
        return self.last_messages.get(topic)

bus = Bus()

def get_time_sec():
    return time.time()
