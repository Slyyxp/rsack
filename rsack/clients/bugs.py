# Standard
import requests
from loguru import logger

from rsack.exceptions import InvokeMapError

class Client:
    def __init__(self):
        self.session = requests.Session()
        self.api_key = "b2de0fbe3380408bace96a5d1a76f800"
        self.session.headers.update({
            "User-Agent": "Mobile|Bugs|4.11.30|Android|5.1.1|SM-G965N|samsung|market",
            "Host": "api.bugs.co.kr",
        })
 
    def auth(self, email: str, password: str):
        """Authenticates session"""
        data = {
            "device_id": "gwAHWlkOYX_T8Sl43N78GiaD6Sg_", # Hardcode device id
            "passwd": password,
            "userid": email
        }
        r = self.make_call("secure", "mbugs/3/login?", data=data)
        if r['ret_code'] == 300:
            logger.critical("Authentication Error, Invalid Credentials")
        else:
            logger.info(f"Login Successful : {r['result']['right']['product']['name']}")
        self.nickname = r['result']['extra_data']['nickname']
        self.connection_info = r['result']['coninfo']
        self.premium = r['result']['right']['stream']['is_flac_premium']
        return self.connection_info

    def make_call(self, sub: str, epoint: str, data: dict = None, json: dict = None, params: dict = None):
        """Makes an API call

        Args:
            sub (str): Subdomain
            epoint (str): Endpoint
            data (dict, optional): POST data. Defaults to None.
            json (dict, optional): POST json. Defaults to None.
            params (dict, optional): POST parameters. Defaults to None.

        Returns:
            dict: Response
        """
        r = self.session.post("https://{}.bugs.co.kr/{}api_key={}".format(sub, epoint, self.api_key), json=json, data=data, params=params)
        return r.json()

    def get_artist(self, id: int) -> dict:
        """Retrieves artist information

        Args:
            id (int): Artists unique id

        Raises:
            InvokeMapError: Failed to invoke map

        Returns:
            dict: API response
        """
        json = [{
            "id": "artist_info",
            "args": {"artistId": id}
        },
                {
                    "id": "artist_album",
                    "args": {"artistId": id,
                             "albumType": "main",
                             "tracksYn": "Y",
                             "page": 1,
                             "size": 500
                            }}]
        r = self.make_call("api", "3/home/invokeMap?", json=json)
        if r['ret_code'] != 0:
            raise InvokeMapError(r)
        return r
    
    def get_album(self, id: int) -> dict:
        """Retrieves album information

        Args:
            id (int): Album unique id.

        Raises:
            InvokeMapError: Failed to invoke map.

        Returns:
            dict: API response.
        """
        json = [{
            "id": "album_info",
            "args": {"albumId": id}
        },
                {
                    "id": "artist_role_info",
                    "args": {"contentsId": id,
                             "type": "ALBUM"
                            }}]
        r = self.make_call("api", "3/home/invokeMap?", json=json)
        if r['ret_code'] != 0:
            raise InvokeMapError(r)
        return r
    
    def get_track(self, id: int) -> dict:
        """Retrieves track information

        Args:
            id (int): Track unique id.

        Raises:
            InvokeMapError: Failed to invoke map.

        Returns:
            dict: API reponse
        """
        json=[{"id":"track_detail", 
               "args":{"trackId":id}
            }]
        r = self.make_call("api", "3/home/invokeMap?", json=json)
        if r['ret_code'] != 0:
            raise InvokeMapError(r)
        return r