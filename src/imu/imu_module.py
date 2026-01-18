import random
import time
from src.core import bus, Message, get_time_sec

class IMUModule:
    def __init__(self, name, topic_name):
        self.name = name
        self.topic_name = topic_name
        self.accel_x = 0.0
        self.accel_y = 0.0
        self.accel_z = 9.81
        self.gyro_x = 0.0
        self.gyro_y = 0.0
        self.gyro_z = 0.0
        
    def step(self):
        msg = Message(
            accel_x = self.accel_x + random.gauss(0, 0.1),
            accel_y = self.accel_y + random.gauss(0, 0.1),
            accel_z = self.accel_z + random.gauss(0, 0.1),
            gyro_x = self.gyro_x + random.gauss(0, 0.01),
            gyro_y = self.gyro_y + random.gauss(0, 0.01),
            gyro_z = self.gyro_z + random.gauss(0, 0.01),
            timestamp = get_time_sec()
        )
        bus.publish(self.topic_name, msg)
