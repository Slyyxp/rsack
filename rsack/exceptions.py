class DeviceIDError():
    def __init__(self):
        message = "Device ID has been changed since last stream resulting in playback error."
    
    def __str__(self):
        return self.message