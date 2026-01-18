from src.params import param_server
from src.core import bus, Message, get_time_sec

class FilterModule:
    def __init__(self):
        self.last_gps_time = 0
        self.last_gps_msg = None
        self.dead_reckoning = True
        
        bus.subscribe("gps_position", self.gps_callback)
        bus.subscribe("imu_1", self.imu1_callback)
        bus.subscribe("imu_2", self.imu2_callback)
        
        self.lat = 37.7749
        self.lon = -122.4194
        self.alt = 100.0
        self.gps_sats = 0 
        
        self.imu1_msg = None
        self.imu2_msg = None
        
        # Filtered acceleration 
        self.accel_x = 0.0
        self.accel_y = 0.0
        self.accel_z = 0.0
        
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.vel_z = 0.0
        
        self.last_step_time = get_time_sec() # Time tracking for integration
        self.meters_to_deg = 1.0 / 111000.0 # Convert meters to degrees for lat/lon

    def gps_callback(self, msg):
        self.last_gps_msg = msg
        self.last_gps_time = msg.timestamp
        self.gps_sats = getattr(msg, 'satellites', 0)

    def imu1_callback(self, msg):
        self.imu1_msg = msg
        self.run_filter_step()

    def imu2_callback(self, msg):
        self.imu2_msg = msg
        self.run_filter_step()
        
    def run_filter_step(self):
        fuse_src = param_server.get_param("FILTER_FUSE_SRC")
        fuse_imu2 = (fuse_src & 2) == 2
        fuse_imu1 = (fuse_src & 4) == 4
        
        ax_sum = 0.0
        ay_sum = 0.0
        az_sum = 0.0
        count = 0
        
        if fuse_imu1 and self.imu1_msg:
            ax_sum += self.imu1_msg.accel_x
            ay_sum += self.imu1_msg.accel_y
            az_sum += self.imu1_msg.accel_z
            count += 1
            
        if fuse_imu2 and self.imu2_msg:
            ax_sum += self.imu2_msg.accel_x
            ay_sum += self.imu2_msg.accel_y
            az_sum += self.imu2_msg.accel_z
            count += 1
            
        if count > 0:
            self.accel_x = ax_sum / count
            self.accel_y = ay_sum / count
            self.accel_z = az_sum / count

    def step(self):
        now = get_time_sec()
        dt = now - self.last_step_time
        self.last_step_time = now
        
        fuse_src = param_server.get_param("FILTER_FUSE_SRC")
        fuse_gps = (fuse_src & 1) == 1
        
        min_sats = param_server.get_param("MIN_GPS_SAT_VAL")
        
        gps_valid = False
        
        if fuse_gps and self.last_gps_msg:
            is_fresh = (now - self.last_gps_time < 0.5)
            has_enough_sats = (self.gps_sats >= min_sats)
            
            if is_fresh and has_enough_sats:
                gps_valid = True
                self.lat = self.last_gps_msg.lat
                self.lon = self.last_gps_msg.lon
                self.alt = self.last_gps_msg.alt
                # Reset velocity when GPS is valid
                self.vel_x = 0.0
                self.vel_y = 0.0
                self.vel_z = 0.0
        
        if gps_valid:
            self.dead_reckoning = False
        else:
            self.dead_reckoning = True
            # Integrate acceleration to velocity
            self.vel_x += self.accel_x * dt
            self.vel_y += self.accel_y * dt
            self.vel_z += (self.accel_z - 9.81) * dt
            
            # Integrate velocity to position
            self.lat += self.vel_y * dt * self.meters_to_deg
            self.lon += self.vel_x * dt * self.meters_to_deg
            self.alt += self.vel_z * dt
        
        msg = Message(
            lat=self.lat,
            lon=self.lon,
            alt=self.alt,
            accel_x=self.accel_x,
            accel_y=self.accel_y,
            accel_z=self.accel_z,
            dead_reckoning=self.dead_reckoning,
            timestamp=now
        )
        bus.publish("vehicle_global_position", msg)
