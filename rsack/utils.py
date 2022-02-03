import os
from re import match
from datetime import datetime
from loguru import logger
from getpass import getpass
from configparser import ConfigParser


class Settings:
    def __init__(self, check=False):
        self.ini_path = os.path.join(get_settings_path(), 'rsack_settings.ini')
        if check:
            logger.debug('Removing settings.ini')
            os.remove(self.ini_path)
        # If settings doesn't exist then create one
        if not os.path.isfile(self.ini_path):
            logger.debug(f'Generating {self.ini_path}')
            self.generate_settings()
        # Read settings.ini
        self.config = ConfigParser()
        self.config.read(self.ini_path)

    @logger.catch
    def generate_settings(self):
        """
        Generates settings.ini based on user input
        """
        # Inputs
        bugs_username = input(
            'Please enter your Bugs.co.kr email: (If none leave blank)\n')
        bugs_password = getpass(
            'Please enter your Bugs.co.kr password: (If none leave blank)\n')
        bugs_threads = input('How many Bugs.co.kr download threads do you want to use?: (2-3 recommended)\n')
        bugs_path = input('Enter your download path for Bugs.co.kr:\n')
        bugs_lyrics = input('Enter your preferred Bugs.co.kr lyrics type: (T = Timed, N = Normal)\n')
        # Write file
        config = ConfigParser()
        config['Bugs'] = {'username': bugs_username,
                          'password': bugs_password,
                          'threads': bugs_threads,
                          'path': bugs_path,
                          'lyrics': bugs_lyrics}
        with open(self.ini_path, 'w+') as configfile:
            config.write(configfile)

    def Bugs(self):
        """
        Returns the contents of the 'Bugs' section of settings.ini as dict.
        """
        return dict(self.config.items('Bugs'))

    def Genie(self):
        """
        Returns the contents of the 'Genie' section of settings.ini as dict.
        """
        return dict(self.config.items('Genie'))


def track_to_flac(track, album, lyrics):
    """Creates dict with appropriate FLAC headers.

    Args:
        track (dict): Dict containing track info from API response
        album (dict): Dict containing album info from API response
        lyrics (str): Lyrics of the track
    """
    meta = {
        "ALBUM": track['album_title'],
        "ALBUMARTIST": track['artist_disp_nm'],
        "ARTIST": track['artist_disp_nm'],
        "TITLE": track['track_title'],
        "DISCNUMBER": str(track['disc_id']),
        "TRACKNUMBER": str(track['track_no']),
        "COMMENT": str(track['track_id']),
        "DATE": _format_date(track['release_ymd']),
        "GENRE": album['Genre'],
        "LABEL": album['Label'],
        "LYRICS": lyrics
    }
    return meta


def _format_date(date):
    # Bugs sometimes does not include the day on the release date for older albums released on the first day of the month.
    # We will append it manuallly before date transformation.
    if len(date) == 6:
        date = date + "01"
    date_patterns = ["%Y%m%d", "%Y%m", "%Y"]
    for pattern in date_patterns:
        try:
            return datetime.strptime(date, pattern).strftime('%Y.%m.%d')
        except ValueError:
            pass


def determine_quality(svc_flac_yn):
    if svc_flac_yn == 'Y':
        return 'flac'
    else:
        return 'mp3'

def get_id(url):
	return match(
		r'https?://music\.bugs\.co\.kr/(?:(?:album|artist|track|playlist)/|[a-z]{2}-[a-z]{2}-?\w+(?:-\w+)*-?)(\w+)',
		url).group(1)
 
def get_settings_path():
    if "XDG_CONFIG_HOME" in os.environ:
        return os.environ['XDG_CONFIG_HOME']
    elif "HOME" in os.environ:
        return os.environ['HOME']
    elif "HOMEDRIVE" in os.environ and "HOMEPATH" in os.environ:
        return os.environ['HOMEDRIVE'] + os.environ['HOMEPATH']
    else:
        return os.path._getfullpathname("./")
