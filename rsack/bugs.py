import os
import requests
from datetime import datetime
from loguru import logger
from mutagen.flac import FLAC, Picture
import mutagen.id3 as id3
from mutagen.id3 import ID3NoHeaderError
from concurrent.futures import ThreadPoolExecutor

from rsack.clients import bugs
from rsack.utils import Settings, track_to_flac, insert_total_tracks, contribution_check, sanitize


class Download:
    def __init__(self, type: str, id: int):
        """Initialize and control flow of download process

        Args:
            type (str): String to declare type of download (album/artist/track).
            id (int): Unique ID.
        """
        self.settings = Settings().Bugs()
        self.client = bugs.Client()
        self.conn_info = self.client.auth(username=self.settings['username'], password=self.settings['password'])
        logger.info(f"Threads: {self.settings['threads']}")
        if type == "artist":
            self._artist(id)
        elif type == "album":
            self._album(id)

    def _artist(self, id: int):
        """Handle artist downloads

        Args:
            id (int): Unique Artist ID
        
        Note:
            self.client.get_artist() returns an album list, but does not include all the necessary tagging info.
            This means it's not worth passing it on and an additional request has to be used.
        """
        artist = self.client.get_artist(id)
        logger.info(f"{len(artist['list'][1]['artist_album']['list'])} releases found")
        for album in artist['list'][1]['artist_album']['list']:
            contribution = contribution_check(id, int(album['artist_id']))
            if contribution:
                if self.settings['contributions'] == 'Y':
                    self._album(album['album_id'])
                else:
                    logger.debug("Skipping album contribution")
            else:
                self._album(album['album_id'])
                
    def _album(self, id: int):
        """Handle album downloads

        Args:
            id (int): Unique album id
        """
        self.album = self.client.get_album(id)['list'][0]['album_info']['result']
        logger.info(f"Album: {self.album['title']}")
        # Acquire disc total
        self.album['disc_total'] = self.album['tracks'][-1]['disc_id']
        # Add track_total to meta.
        insert_total_tracks(self.album['tracks'])
        self._album_path()
        self._download_cover()
        # Begin downloading tracks
        with ThreadPoolExecutor(max_workers=int(self.settings['threads'])) as executor:
            executor.map(self._download, self.album['tracks'])
    
    @logger.catch
    def _album_path(self):
        """Creates necessary directories"""
        if self.settings['artist_folders'].upper() == 'Y':
            self.album_path = os.path.join(
                self.settings['path'], sanitize(self.album['artist_disp_nm']), f"{sanitize(self.album['artist_disp_nm'])} - {sanitize(self.album['title'])}")
        else:
            self.album_path = os.path.join(
                self.settings['path'], f"{sanitize(self.album['artist_disp_nm'])} - {sanitize(self.album['title'])}")
        try:
            if not os.path.exists(self.album_path):
                logger.debug(f"Creating {self.album_path}")
                os.makedirs(self.album_path)
        except OSError as exc:
            if exc.errno == 36: # Exceeded path limit
                if len(self.album['artist_disp_name']) > len(self.album['title']): #  Check whether artist name or album name is the issue
                    self.album['artist_disp_name'] = "Various Artists" # Change to V.A. as Bugs has likely compiled a huge list of artists
                    logger.debug("Artist name forcibly changed to Various Artists.")
                else: # If title is the issue
                    logger.debug("Album title forcibly changed as it exceeded the allowed Path length.")
                    self.album['title'] = "EDIT ME"
        
                # Reassign album path
                if self.settings['artist_folders'].upper() == 'Y':
                    self.album_path = os.path.join(
                        self.settings['path'], sanitize(self.album['artist_disp_nm']), f"{sanitize(self.album['artist_disp_nm'])} - {sanitize(self.album['title'])}")
                else:
                    self.album_path = os.path.join(
                        self.settings['path'], f"{sanitize(self.album['artist_disp_nm'])} - {sanitize(self.album['title'])}")

                # Retry
                if not os.path.exists(self.album_path):
                    logger.debug(f"Creating {self.album_path}")
                    os.makedirs(self.album_path)
                    
        # Create nested disc folders
        if self.album['disc_total'] > 1:
            self.discs = True
            for i in range(self.album['disc_total']):
                d = os.path.join(self.album_path, f"Disc {str(i + 1)}")
                if not os.path.exists(d):
                    os.makedirs(d)
        else: 
            self.discs = False

    @logger.catch
    def _download(self, track: dict):
        """Downloads track

        Args:
            track (dict): Contains track information from API response
        """
        logger.info(f"Track: {track['track_title']}")
        if self.discs:
            file_path = os.path.join(self.album_path, f"Disc {str(track['disc_id'])}", f"{track['track_no']}. {sanitize(track['track_title'])}.temp")
        else:
            file_path = os.path.join(self.album_path, f"{track['track_no']}. {sanitize(track['track_title'])}.temp")
        if self._exist_check(file_path):
            logger.debug(f"{track['track_title']} already exists")
        else:
            # Create params required to request the track
            params = {
                "ConnectionInfo": self.conn_info,
                "api_key": self.client.api_key,
                "overwrite_session": "Y",
                "track_id": track['track_id']
            }
            # Create headers for byte position.
            headers = {
                "Range": 'bytes=%d-' % self._return_bytes(file_path),
            }
            r = requests.get(f"http://api.bugs.co.kr/3/tracks/{track['track_id']}/listen/android/flac", headers=headers, params=params, stream=True)
            if r.url.split("?")[0].endswith(".mp3"): # If response redirects to MP3 file set quality to .mp3
                quality = '.mp3'
            elif r.url.split("?")[0].endswith(".m4a"):
                quality = '.m4a' 
            else: # Otherwise .flac
                quality = '.flac'
            if quality != '.m4a':
                if r.status_code == 404:
                    logger.info(f"{track['track_title']} unavailable")
                else:
                    with open(file_path, 'ab') as f:
                        for chunk in r.iter_content(32 * 1024):
                            if chunk:
                                f.write(chunk)
                    c_path = file_path.replace(".temp", quality)
                    os.rename(file_path, c_path)
                    self._tag(track, c_path)
            else:
                logger.info(f"{track['track_title']} is unavailable.")

    @staticmethod
    def _return_bytes(file_path: str) -> int:
        """Returns number of bytes in file

        Args:
            file_path (str): File path

        Returns:
            int: Returns size in bytes
        """
        
        if os.path.exists(file_path):
            logger.debug(f"Existing .temp file {os.path.basename(file_path)} has resumed.")
            return os.path.getsize(file_path)
        else:
            return 0
    
    @staticmethod
    def _exist_check(file_path: str) -> bool:
        """Check if file exists for both possible cases

        Args:
            file_path (str): .temp file path

        Returns:
            bool: True if exists else false
        """
        if os.path.exists(file_path.replace('.temp', '.mp3')):
            return True
        if os.path.exists(file_path.replace('.temp', '.flac')):
            return True
        else:
            return False
    
    def _download_cover(self):
        """Downloads cover artwork"""
        self.cover_path = os.path.join(self.album_path, 'cover.jpg')
        if os.path.exists(self.cover_path):
            logger.info('Cover already exists')
        else:
            r = requests.get(self.album['img_urls'][self.settings['cover_size']])
            r.raise_for_status
            with open(self.cover_path, 'wb') as f:
                f.write(r.content)
            logger.info('Cover artwork downloaded.')
    
    @logger.catch
    def _tag(self, track: dict, file_path: str):
        """Append ID3/FLAC tags

        Args:
            track (dict): API response containing track information
            file_path (str): File being tagged
        """
        lyrics = self._get_lyrics(track['track_id'], track['lyrics_tp'])
        tags = track_to_flac(track, self.album, lyrics)
        if str(file_path).endswith('.flac'):
            f_file = FLAC(file_path)
            # Add cover artwork to flac file
            if self.cover_path:
                f_image = Picture()
                f_image.type = 3
                f_image.desc = 'Front Cover'
                with open(self.cover_path, 'rb') as f:
                    f_image.data = f.read()
                f_file.add_picture(f_image)
            logger.debug(f"Writing tags to {file_path}")
            for k, v in tags.items():
                f_file[k] = str(v)
            f_file.save()
        if str(file_path).endswith('.mp3'):
            # Legend contains all ID3 tags for each FLAC header.
            legend = {
                "ALBUM": id3.TALB,
                "ALBUMARTIST": id3.TPE2,
                "ARTIST": id3.TPE1,
                "COMMENT": id3.COMM,
                "COMPOSER": id3.TCOM,
                "COPYRIGHT": id3.TCOP,
                "DATE": id3.TDRC,
                "GENRE": id3.TCON,
                "ISRC": id3.TSRC,
                "LABEL": id3.TPUB,
                "PERFORMER": id3.TOPE,
                "TITLE": id3.TIT2,
                "LYRICS": id3.USLT
            }
            try:
                m_file = id3.ID3(file_path)
            except ID3NoHeaderError:
                m_file = id3.ID3()
            logger.debug(f"Writing tags to {file_path}")
            # Apply tags using the legend
            for k, v in tags.items():
                try:
                    id3tag = legend[k]
                    m_file[id3tag.__name__] = id3tag(encoding=3, text=v)
                except KeyError:
                    continue
            # Track and disc numbers
            m_file.add(id3.TRCK(encoding=3, text=f"{track['track_no']}/{track['track_total']}"))
            m_file.add(id3.TPOS(encoding=3, text=f"{track['disc_id']}/{self.album['disc_total']}"))
            # Apply cover artwork
            if self.cover_path:
                with open(self.cover_path, 'rb') as cov_obj:
                    m_file.add(id3.APIC(3, 'image/jpg', 3, '', cov_obj.read()))
            m_file.save(file_path, 'v2_version=3')

    def _get_lyrics(self, track_id: int, lyrics_tp: str) -> str:
        """Retrieves and formats track lyrics

        Args:
            track_id (int): Unique track ID.
            lyrics_tp (str): 'T'/'N': Timed/Normal lyrics from settings.

        Returns:
            str: Formatted lyrics
        """
        # If user prefers timed then retrieve timed lyrics
        if lyrics_tp == 'T' and self.settings['lyrics'] == 'T':
            # Retrieve timed lyrics
            r = requests.get(f"https://music.bugs.co.kr/player/lyrics/T/{track_id}")
            # Format timed lyrics
            lyrics = r.json()['lyrics'].replace("＃", "\n")
            line_split = (line.split('|') for line in lyrics.splitlines())
            lyrics = ("\n".join(
                f'[{datetime.fromtimestamp(round(float(a), 2)).strftime("%M:%S.%f")[0:-4]}]{b}' for a, b in line_split))
        # If user prefers untimed or timed unavailable then use untimed
        elif lyrics_tp == 'N' or self.settings['lyrics'] == 'N':
            r = requests.get(f'https://music.bugs.co.kr/player/lyrics/N/{track_id}')
            lyrics = r.json()['lyrics']
            # If unavailable leave as empty string
            if lyrics_tp is None:
                lyrics = ""
        else:
            lyrics = ""
        return lyrics