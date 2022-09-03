import json
import requests

from loguru import logger
from rsack.exceptions import DeviceIDError

class Client:
    def __init__(self):
        self.session = requests.Session()
        self.dev_id = "eb9d53a3c424f961"

        self.session.headers.update({
            "User-Agent": "genie/ANDROID/5.1.1/WIFI/SM-G930L/dreamqltecaneb9d53a3c424f961/500200714/40807",
            "Referer": "app.genie.co.kr"
        })

        self.session.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))
        
    def make_call(self, sub: str, epoint: str, data: dict) -> dict:
        """Makes API call to specified endpoint

        Args:
            sub (str): Subdomain
            epoint (str): Endpoint
            data (dict): POST data
        
        Endpoints used:
            player/j_StmInfo.json: Returns track information
            member/j_Member_Login.json: Authentication.
            song/j_AlbumSongList.json: Returns album information

        Returns:
            dict: JSON Response
        """
        try:
            r = self.session.post("https://{}.genie.co.kr/{}".format(sub, epoint), data=data)
        except requests.exceptions.ConnectionError:
            logger.debug("Remote end closed connection, retrying.")
            r = self.session.post("https://{}.genie.co.kr/{}".format(sub, epoint), data=data)
        return r.json()

    def auth(self, username: str, password: str):
        """
        Authenticate session
        """
        data = {
            "uxd": username,
            "uxx": password
        }
        r = self.make_call("app", "member/j_Member_Login.json", data)
        if r['Result']['RetCode'] != "0":
            logger.critical("Authentication failed.")
        else:
            logger.info("Login Successful.")
        self.usr_num = r['DATA0']['MemUno']
        self.usr_token = r['DATA0']['MemToken']
        self.stm_token = r['DATA0']['STM_TOKEN']

    def get_album(self, id: int) -> dict:
        """Retrieve album information"""
        data = {
            "axnm": id,
            "dcd": self.dev_id,
            "mts": "Y",
            "stk": self.stm_token,
            "svc": "IV",
            "tct": "Android",
            "unm": self.usr_num,
            "uxtk": self.usr_token
        }
        r = self.make_call("app", "song/j_AlbumSongList.json", data)
        if r['Result']['RetCode'] != "0":
            logger.critical("Failed to retrieve metadata")
        return r
    
    def get_artist_albums(self, id: int) -> dict:
        """Retrieve artists album information"""
        data = {
            "uxtk": self.usr_token,
            "sign": "Y",
            "tct": "Android",
            "svc": "IV",
            "stk": self.stm_token,
            "dcd": self.dev_id,
            "xxnm": id,
            "unm": self.usr_num,
            "mts": "Y",
            "pgsize": 500
        }
        r = self.make_call("app", "song/j_ArtistAlbumList.json", data)
        if r['Result']['RetCode'] != "0":
            logger.critical("Failed to retrieve metadata")
        return r

    def get_artist(self, id: int) -> dict:
        """Retrieves artist information"""
        data = {
            "uxtk": self.usr_token,
            "sign": "Y",
            "tct": "Android",
            "svc": "IV",
            "stk": self.stm_token,
            "dcd": self.dev_id,
            "xxnm": id,
            "unm": self.usr_num,
            "mts": "Y"
        }
        r = self.make_call("info", "info/artist", data)
        if r['result']['ret_code'] != "0":
            logger.critical("Failed to retrieve metadata")
        return r
        
    def get_stream_meta(self, id: int) -> dict:
        """Retrieves information on a streamable track

        Args:
            id (int): Unique ID of track

        Raises:
            DeviceIDError: Raises when RetCode "A00003" is returned.
                        Caused by sudden change in DeviceID.
                              
        Returns:
            dict: JSON Response
        """
        data = {
            "bitrate": "24bit",
            "sign": "Y",
            "mts": "Y",
            "dcd": self.dev_id,
            "stk": self.stm_token,
            "itn": "Y",
            "svc": "IV",
            "unm": self.usr_num,
            "uxtk": self.usr_token,
            "xgnm": id,
            "apvn": 40807
        }
        r = self.make_call("stm", "player/j_StmInfo.json", data)
        if r['Result']['RetCode'] == "A00003":
            raise DeviceIDError("Device ID has been changed since last stream.")
        if r['Result']['RetCode'] != "0":
            logger.critical("Failed to retrieve metadata")
        if r['Result']['RetCode'] == "S00001":
            logger.debug("This content is currently unavailable for service")
            return False
        return r['DataSet']['DATA'][0]
    
    def get_timed_lyrics(self, id: str) -> dict:
        """Retrieve the timed lyrics for a track"""
        r = self.session.get(f"https://dn.genie.co.kr/app/purchase/get_msl.asp?songid={id}&callback=GenieCallBack")
        if r.content.decode('utf-8') == 'NOT FOUND LYRICS':
            return None
        # Remove unwanted characters
        r = r.content.decode('utf-8')[14:-2]
        return json.loads(r)