from requests.models import Response

class DeviceIDError(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self) -> str:
        return self.message

class InvokeMapError(Exception):
    def __init__(self, response: Response):
        self.message = response['ret_detail_msg']
    
    def __str__(self) -> str:
        return self.message
    
class InvalidURL(Exception):
    def __init__(self, url: str):
        self.url = url
    
    def __str__(self) -> str:
        return f"{self.url} is invalid."    