import random
import time

class GPSDriver:
    def __init__(self):
        self.true_lat = 37.7749
        self.true_lon = -122.4194
        self.alt = 100.0
        
        self.last_update = time.time()
        self.mode = 0
        self.next_transition = time.time() + 5.0 
        
        self.drift_lat = 0.0
        self.drift_lon = 0.0
        self.jump_lat = 0.0
        self.jump_lon = 0.0
        
        self.sats = random.randint(16, 22)
        self.uncertainty = random.uniform(0.1, 0.5)
        
    def get_data(self):
        now = time.time()
        
        self.drift_lat += (random.random() - 0.5) * 0.00001
        self.drift_lon += (random.random() - 0.5) * 0.00001
        
        if now >= self.next_transition:
            if self.mode == 0:
                self.mode = 1
                duration = random.uniform(3.0, 8.0)
                self.next_transition = now + duration
                self.jump_lat = (random.random() - 0.5) * 0.0005 
                self.jump_lon = (random.random() - 0.5) * 0.0005
                self.sats = random.randint(4, 9)
                self.uncertainty = random.uniform(5.0, 15.0)
            else:
                self.mode = 0
                duration = random.uniform(5.0, 25.0)
                self.next_transition = now + duration
                self.jump_lat = 0.0
                self.jump_lon = 0.0
                self.sats = random.randint(16, 22)
                self.uncertainty = random.uniform(0.1, 0.5)
            
        return {
            'lat': self.true_lat + self.drift_lat + self.jump_lat,
            'lon': self.true_lon + self.drift_lon + self.jump_lon,
            'alt': self.alt,
            'satellites': self.sats,
            'uncertainty': self.uncertainty
        }
