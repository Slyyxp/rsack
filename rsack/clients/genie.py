import requests
from loguru import logger

class Client:

    def __init__(self):
        self.session = requests.Session()
        self.dev_id = "eb9d53a3c424f961"

        self.session.headers.update({
            "User-Agent": "genie/ANDROID/5.1.1/WIFI/SM-G930L/dreamqltecaneb9d53a3c424f961/500200714/40807",
            "Referer": "app.genie.co.kr"
        })

    def make_call(self, sub, epoint, data):
        """
        :param sub: Url Prefix
        :param epoint: Endpoint
        :param data: Post data
        :return: API Response
        Endpoints used:
                player/j_StmInfo.json - Provides information on the streamed track.
                member/j_Member_Login.json - Authentication.
                song/j_AlbumSongList.json - Provides album information.
        """
        r = self.session.post(
            "https://{}.genie.co.kr/{}".format(sub, epoint), data=data)
        r.raise_for_status()

        return r.json()

    def auth(self, username, password):
        """
        Authenticate our session appearing as an Android device
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

    def get_album(self, id):
        """
        :param id: Album ID.
        :return: API Response containing album metadata.
        """
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
    
    def get_artist(self, id):
        """Returns artist information

        Args:
            id (int): Artist UID

        Returns:
            [dict]: API Response containing artist information
        """
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
        r = self.make_call("app", "song/j_ArtistAlbumList.json", data)
        if r['Result']['RetCode'] != "0":
            logger.critical("Failed to retrieve metadata")
        return r

    def get_stream_meta(self, id, q=None):
        """
        :param id: Album ID
        :param q: Album quality.
        :return: API Response containing metadata for the currently streamed track.
        Quality options:
                1 - MP3
                2 - 16bit FLAC
                3 - 24bit FLAC
        """
        if q is None:
            q = '24bit'
        data = {
            "bitrate": q,
            "dcd": self.dev_id,
            "stk": self.stm_token,
            "svc": "IV",
            "unm": self.usr_num,
            "uxtk": self.usr_token,
            "xgnm": id
        }
        r = self.make_call("stm", "player/j_StmInfo.json", data)
        if r['Result']['RetCode'] == "A00003":
            logger.critical("Device ID has changed since last stream resulting in playback error.")
        if r['Result']['RetCode'] != "0":
            logger.critical("Failed to retrieve metadata")
        if r['Result']['RetCode'] == "S00001":
            logger.debug("This content is currently unavailable for service")
        return r['DataSet']['DATA'][0]
