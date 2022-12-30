import os
from sys import exit
from platform import system
from re import match, sub
from datetime import datetime
from loguru import logger
from configparser import ConfigParser

from rsack.exceptions import InvalidURL

class Settings:
    def __init__(self, check=False):
        self.ini_path = os.path.join(get_settings_path(), 'rsack_settings.ini')
        # If settings doesn't exist then create one
        if not os.path.isfile(self.ini_path):
            logger.debug(f'Writing {self.ini_path}')
            self.generate_settings()
        # Read settings.ini
        self.config = ConfigParser()
        self.config.read(self.ini_path)

    @logger.catch
    def generate_settings(self):
        """
        Generates settings.ini based on user input
        """
        # Write file
        config = ConfigParser()
        config['Bugs'] = {'email': "email@protonmail.com",
                          'password': "mypassword",
                          'threads': "2",
                          'path': "C:\Music\Korean",
                          'timed_lyrics': "true",
                          'contributions': "false",
                          "cover_size": "original",
                          "template": "/{artist}/{artist} - {title}"}
        
        config['Genie'] = {'username': "username",
                           'password': "mypassword",
                           'threads': "2",
                           'path': "C:\Music\Korean",
                           'artist_folders': "Y",
                           'timed_lyrics': "Y",
                           'contributions': "N",
                           "template": "/{artist}/{artist} - {title}"}
        
        config['KKBox'] = {"email": "email@protonmail.com",
                           "password": "mypassword",
                           "threads": "2",
                           "path": "C:\Music\KKBox",
                           "template": "/{artist}/{artist} - {title}"}
        
        with open(self.ini_path, 'w+') as configfile:
            config.write(configfile)
        exit()

    def _str_to_boolean(self, section: str, d: dict) -> dict:
        """Iterates dict converting possible boolean values

        Args:
            section (str): Section header
            d (dict): Dictionary to iterate

        Returns:
            dict: Dictionary with string values replaced with boolean
        """
        for k in d:
            try:
                d[k] = self.config.getboolean(section, k)
            except ValueError: # Not a boolean
                pass
        return d
        
    def Bugs(self) -> dict:
        """
        Returns the contents of the 'Bugs' section of settings.ini as dict.
        """
        return self._str_to_boolean(section='Bugs', d=dict(self.config.items('Bugs')))

    def Genie(self) -> dict:
        """
        Returns the contents of the 'Genie' section of settings.ini as dict.
        """
        return self._str_to_boolean(section='Genie', d=dict(self.config.items('Genie')))
    
    def KKBox(self) -> dict:
        """
        Returns the contents of the 'KKBox' section of settings.ini as dict.
        """
        return self._str_to_boolean(section='KKBox', d=dict(self.config.items('KKBox')))


def track_to_flac(track: dict, album: dict, lyrics: str) -> dict:
    """Creates dict with appropriate FLAC headers.

    Args:
        track (dict): Dict containing track info from API response
        album (dict): Dict containing album info from API response
        lyrics (str): Lyrics of the track
    """
    meta = {
        "ALBUM": track['album_title'],
        "ALBUMARTIST": album['artist_disp_nm'],
        "ARTIST": track['artist_disp_nm'],
        "TITLE": track['track_title'],
        "DISCNUMBER": str(track['disc_id']),
        "DISCTOTAL": str(album['disc_total']),
        "TRACKNUMBER": str(track['track_no']),
        "TRACKTOTAL": str(track['track_total']),
        "COMMENT": str(track['track_id']),
        "DATE": _format_date(track['release_ymd']),
        "GENRE": album['genre_str'],
        "LABEL": '; '.join(str(label['label_nm']) for label in album['labels']),
        "LYRICS": lyrics
    }
    return meta

def _format_date(date):
    """Formats album release date to preferred format"""
    # Append release day if not present.
    if len(date) == 6:
        date = date + "01"
    date_patterns = ["%Y%m%d", "%Y%m", "%Y"]
    for pattern in date_patterns:
        try:
            return datetime.strptime(date, pattern).strftime('%Y.%m.%d')
        except ValueError:
            pass

def bugs_id(url: str) -> str:
    return match(
        r'https?://music\.bugs\.co\.kr/(?:(?:album|artist|track|playlist)/|[a-z]{2}-[a-z]{2}-?\w+(?:-\w+)*-?)(\w+)',url).group(1)

def genie_id(url: str) -> match:
    expression = r"https://genie.co.kr/detail/(artistInfo|albumInfo)......([0-9]*)"
    result = match(expression, url)
    # This shouldn't be needed, regex needs to be fixed.
    if not result:
        expression = r"https://www.genie.co.kr/detail/(artistInfo|albumInfo)......([0-9]*)"
        result = match(expression, url)
    if result:
        return result
    raise InvalidURL(url)
 
def get_settings_path() -> str:
    """Returns path of home folder to store settings.ini"""
    if "XDG_CONFIG_HOME" in os.environ:
        return os.environ['XDG_CONFIG_HOME']
    elif "HOME" in os.environ:
        return os.environ['HOME']
    elif "HOMEDRIVE" in os.environ and "HOMEPATH" in os.environ:
        return os.environ['HOMEDRIVE'] + os.environ['HOMEPATH']
    else:
        return os.path._getfullpathname("./")

def get_ext(type: str) -> str:
    """Return the filetype.

    Args:
        type (str): "FILE_EXT" from player/j_StmInfo.json response
            Known FILE_EXT's:
                        F96: FLAC 24bit/96kHz
                        F44: FLAC 24bit/44.1kHz
                        FLA: FLAC 16bit
                        MP3: MP3
                        
    Returns:
        str: File extension
    """
    if type == "MP3":
        return ".mp3"
    else:
        return ".flac"

def insert_total_tracks(tracks: list[dict]):
    """Add total_tracks to track metadata"""
    total_tracks_by_disc_id = {}
    for track in tracks:
        if track["disc_id"] not in total_tracks_by_disc_id:
            total_tracks_by_disc_id[track["disc_id"]] = 0
        total_tracks_by_disc_id[track["disc_id"]] += 1

    for track in tracks:
        track["track_total"] = total_tracks_by_disc_id[track["disc_id"]]

def _is_win() -> bool:
	if system() == 'Windows':
		return True

def sanitize(fn: str) -> str:
    """Sanitizes filenames based on Operating System"""
    if _is_win():
        return sub(r'[\/:*?"><|]', '_', fn).strip('. ')
    else:
        return sub('/', '_', fn).strip()

def contribution_check(artist_id_provided: int, artist_id_api: int) -> bool:
    """Checks if artist is contributing"""
    if artist_id_provided == artist_id_api:
        return False
    else:
        return True

def format_genie_lyrics(lyrics: dict) -> str:
    """Convert Genie dict to a usable str format for tagging"""
    # Convert millisecond keys to format [00:00.00][minutes:seconds.milliseconds]
    lines = [f"[{datetime.fromtimestamp(int(x)/1000).strftime('%M:%S.%f')[:-4]}]{lyrics[x]}" for x in lyrics]
    return '\n'.join(lines)