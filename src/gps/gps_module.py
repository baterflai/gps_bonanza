from src.params import param_server
from src.core import bus, Message, get_time_sec
from src.lib.gps_driver import GPSDriver

class GPSModule:
    def __init__(self):
        self.driver = GPSDriver()
        self.last_pub_time = 0
    
    def step(self):
        avail_param = param_server.get_param("GPS_AVAIL")
        if not (avail_param & 1):
            return

        freq = param_server.get_param("GPS_PUB_FREQ")
        if freq == 0:
            return
            
        period = 1.0 / freq
        now = get_time_sec()
        
        if now - self.last_pub_time >= period:
            data = self.driver.get_data()
            
            msg = Message(
                lat=data['lat'],
                lon=data['lon'],
                alt=data['alt'],
                satellites=data['satellites'],
                uncertainty=data['uncertainty'],
                timestamp=now
            )
            bus.publish("gps_position", msg)
            self.last_pub_time = now
