import os
import requests
from datetime import datetime
from loguru import logger
from mutagen.flac import FLAC, Picture
import mutagen.id3 as id3
from mutagen.id3 import ID3NoHeaderError
from concurrent.futures import ThreadPoolExecutor

from rsack.clients import bugs
from rsack.utils import Settings, track_to_flac, determine_quality, insert_total_tracks


class Download:

    def __init__(self, type, id):
        """Initialize download

        Args:
            type (str): Release type (album/artist/track)
            id (int/str): UID of album/artist/track
        """
        # Initialize the type and ID of the release
        self.type = type
        self.id = id
        self.settings = Settings().Bugs()

        # Create and authorize the client
        self.client = bugs.Client(self.settings)
        self.conn_info = self.client.auth()
        self.api_key = self.client.get_api_key()
        
        # Grab the metadata
        self.meta = self.collect()
        # Acquire disc total by finding the last track entry and tacking the disc number
        self.meta['disc_total'] = self.meta['Tracks'][-1]['disc_id']
        # Add track_total to meta.
        insert_total_tracks(self.meta['Tracks'])
        
        
        # Construct album path
        self.album_path = os.path.join(
            self.settings['path'], self.meta['Album_artist'], f"{self.meta['Album_artist']} - {self.meta['Album']}")
        if not os.path.exists(self.album_path):
            logger.debug(f"Creating {self.album_path}")
            os.makedirs(self.album_path)
        else:
            pass

        # Download album cover
        self.cover_path = self._download_cover(self.album_path)

        # Begin downloading tracks
        logger.info(f"Threads: {self.settings['threads']}")
        with ThreadPoolExecutor(max_workers=int(self.settings['threads'])) as executor:
            executor.map(self._download, self.meta['Tracks'])


    def _download(self, track):
        """Downloads the track and passes it on for tagging

        Args:
            track ([dict]): Track metadata provided in API response
        """
        track_id = track['track_id']
        logger.debug(f"Processing: {track_id}")
        # Create params required to request the track
        params = {
            "ConnectionInfo": self.conn_info,
            "api_key": self.api_key,
            "overwrite_session": "Y",
            "track_id": track_id
        }
        # Request track
        r = requests.get(
            "http://api.bugs.co.kr/3/tracks/{}/listen/android/flac".format(
                track_id),
            params=params, stream=True)
        if r.status_code == 404:
            logger.info(f"{track['track_title']} unavailable, skipping.")
        else:
            # Directory management
            file_path = os.path.join(
                self.album_path, f"{track['track_title']}.{determine_quality(track['svc_flac_yn'])}")
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(32 * 1024):
                    if chunk:
                        f.write(chunk)
            self._tag(track, file_path)
            logger.info(f"{track['track_title']} downloaded and tagged")

    def _download_cover(self, path):
        """Downloads album artwork

        Args:
            path ([path]): Path of folder to download to

        Returns:
            [path]: Path of .jpg file
        """
        cover_path = os.path.join(path, 'cover.jpg')
        if os.path.exists(cover_path):
            logger.info('Cover already exists, skipping.')
        else:
            r = requests.get(self.meta['Cover_url']['500'])
            r.raise_for_status
            with open(cover_path, 'wb') as f:
                f.write(r.content)
            logger.info('Cover artwork downloaded.')
        return cover_path

    def _tag(self, track, file_path):
        """Applies appropriate tags to the audio file

        Args:
            track ([dict]): Dict containing track information
            file_path ([path]): Path of .flac or .mp3 file
        """
        lyrics = self._get_lyrics(track['track_id'], track['lyrics_tp'])
        tags = track_to_flac(track, self.meta, lyrics)
        # If file is FLAC
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
        # If file is MP3
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
            m_file.add(id3.TPOS(encoding=3, text=f"{track['disc_id']}/{self.meta['disc_total']}"))
            # Apply cover artwork
            if self.cover_path:
                with open(self.cover_path, 'rb') as cov_obj:
                    m_file.add(id3.APIC(3, 'image/jpg', 3, '', cov_obj.read()))
            m_file.save(file_path, 'v2_version=3')

    def _get_lyrics(self, track_id, lyrics_tp):
        """Retrieves and formats track lyrics

        Args:
            track_id ([int/str]): UID of the track
            lyrics_tp ([str]): 'T' or 'N' is provided in the API reponse, pass this. (T = Timed, N = Normal) 

        Returns:
            [str]: Formatted lyrics
        """
        # If user prefers timed then retrieve timed lyrics
        if lyrics_tp and self.settings['lyrics'] == 'T':
            # Retrieve timed lyrics
            r = requests.get(
                f"https://music.bugs.co.kr/player/lyrics/T/{str(track_id)}")
            # Format timed lyrics
            lyrics = r.json()['lyrics'].replace("＃", "\n")
            line_split = (line.split('|') for line in lyrics.splitlines())
            lyrics = ("\n".join(
                f'[{datetime.fromtimestamp(round(float(a), 2)).strftime("%M:%S.%f")[0:-4]}]{b}' for a, b in
                line_split))
        # If user prefers untimed or the only available is untimed then use untimed
        if 'lyrics_tp' or self.settings['lyrics'] == "N":
            r = requests.get(
                'https://music.bugs.co.kr/player/lyrics/N/{}'.format(str(track_id)))
            lyrics = r.json()['lyrics']
            # If unavailable leave as empty string
            if lyrics_tp is None:
                lyrics = ""
        return lyrics

    def collect(self):
        """Returns specified metadata from Bugs.co.kr API

        Args:
            type (string): specify the release type, album/artist/track
            id (int/string): unique identifier of the album, artist or track.

        Returns:
            [dict]: dict containing usable metadata for tagging
        """
        meta = self.client.get_meta(type=self.type, id=int(self.id))
        return self._clean(meta)

    def _clean(self, meta):
        """Cuts out all unnecessary data and returns

        Args:
            meta ([dict]): Metadata provided in api response

        Returns:
            [dict]: Cleaned metadata
        """
        clean_meta = {"Album": meta['list'][0]['album_info']['result']['artist_disp_nm'],
                      "Album_artist": meta['list'][0]['album_info']['result']['artist_disp_nm'],
                      "Genre": meta['list'][0]['album_info']['result']['genre_str'].replace(",", "; "),
                      "Label": '; '.join(str(label['label_nm']) for label in meta['list'][0]['album_info']['result']['labels']),
                      "Cover_url": meta['list'][0]['album_info']['result']['img_urls'],
                      "Tracks": meta['list'][0]['album_info']['result']['tracks'],
                      }
        return clean_meta
