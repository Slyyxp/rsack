# Standard
import requests
from loguru import logger

class Client:
    def __init__(self):
        self.session = requests.Session()
        self.api_key = "b2de0fbe3380408bace96a5d1a76f800"
        self.session.headers.update({
            "User-Agent": "Mobile|Bugs|4.11.30|Android|5.1.1|SM-G965N|samsung|market",
            "Host": "api.bugs.co.kr",
        })
 
    def auth(self, username: str, password: str):
        """Authenticates session"""
        self.username = username
        self.password = password
        data = {
            "device_id": "gwAHWlkOYX_T8Sl43N78GiaD6Sg_", # Hardcode device id
            "passwd": password,
            "userid": username
        }
        r = self.make_call("secure", "mbugs/3/login?", data=data)
        if r['ret_code'] == 300:
            logger.critical("Authentication Error, Invalid Credentials")
        else:
            logger.info("Login Successful")
        self.nickname = r['result']['extra_data']['nickname']
        self.connection_info = r['result']['coninfo']
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

    @logger.catch
    def get_meta(self, type: str, id: int) -> dict:
        """Retrieves metadata

        Args:
            type (str): Information type. (artist/album/track)
            id (int): Unique ID

        Raises:
            logger.critical: Raised when JSON contains invalid data. Usually the ID passed.

        Returns:
            dict: Response
        """
        if type == "album":
            json=[{"id":"album_info","args":{"albumId":id}}, {"id":"artist_role_info","args":{"contentsId":id,"type":"ALBUM"}}]
        elif type == "artist":
            json=[{"id":"artist_info","args":{"artistId":id}}, {"id":"artist_album","args":{"artistId":id, "albumType":"main","tracksYn":"Y","page":1,"size":500}}]
        elif type == "track":
            json=[{"id":"track_detail", "args":{"trackId":id}}]
        else:
            logger.critical("Invalid invokeMap type.")
        r = self.make_call("api", "3/home/invokeMap?", json=json)
        if r['ret_code'] != 0:
            raise logger.critical("Failed to get a map.")
        return r