class ParameterServer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ParameterServer, cls).__new__(cls)
            cls._instance.params = {
                "FILTER_FUSE_SRC": 6,     # Default: IMU1=1, IMU2=1, GPS=0
                "GPS_PUB_FREQ": 1,        # Default: 1 Hz
                "GPS_AVAIL": 1,           # Default: Available
                "MIN_GPS_SAT_VAL": 0      # Default: 0 
            }
        return cls._instance

    def get_param(self, name):
        return self.params.get(name)

    def set_param(self, name, value):
        if name in self.params:
            self.params[name] = int(value)
        else:
            print(f"Unknown parameter: {name}")

param_server = ParameterServer()
