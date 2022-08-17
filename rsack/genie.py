import os
import mutagen.id3 as id3
from loguru import logger
from urllib.parse import unquote
from mutagen.flac import FLAC
from concurrent.futures import ThreadPoolExecutor
from requests.models import Response

from rsack.clients import genie
from rsack.utils import Settings, format_genie_lyrics, get_ext, sanitize, format_genie_lyrics


class Download:
    def __init__(self, type: str, id: int):
        """Initialize and control the flow of the download"""
        self.settings = Settings().Genie()
        self.client = genie.Client()
        self.client.auth(username=self.settings['username'], password=self.settings['password'])
        self.meta = self._collect(type, id)
        logger.info(f"Threads: {self.settings['threads']}")
        if type == "artist":
            self._artist()
        elif type == "album":
            self._album(id)

    def _artist(self):
        """Iterate albums in artist"""
        for album in self.meta['DataSet']['DATA']:
            self._album(album['ALBUM_ID'])

    @logger.catch
    def _album(self, id: int):
        """Iterate tracks in album"""
        meta = self.client.get_album(id)
        logger.info(f"Album: {unquote(meta['DATA0']['DATA'][0]['ALBUM_NAME'])}")
        artist_name = sanitize(unquote(meta['DATA0']['DATA'][0]['ARTIST_NAME']))
        if self.settings['artist_folders'].upper() == 'Y':
            self.album_path = os.path.join(
                self.settings['path'], artist_name, f"{artist_name} - {sanitize(unquote(meta['DATA0']['DATA'][0]['ALBUM_NAME']))}")
        else:
            self.album_path = os.path.join(
                self.settings['path'], f"{artist_name} - {sanitize(unquote(meta['DATA0']['DATA'][0]['ALBUM_NAME']))}")
        if not os.path.isdir(self.album_path):
            os.makedirs(self.album_path)
        self._download_cover(unquote(meta['DATA0']['DATA'][0]['ALBUM_IMG_PATH_600']))

        # Create dict containing relevant album information for tagging.
        self.album_meta = {
            "album_title": meta['DATA0']['DATA'][0]['ALBUM_NAME'],
            "track_total": len(meta['DATA1']['DATA']),
            "album_artist": unquote(meta['DATA0']['DATA'][0]['ARTIST_NAME']),
            "release_date": meta['DATA0']['DATA'][0]['ALBUM_RELEASE_DT'],
            "planning": unquote(meta['DATA0']['DATA'][0]['ALBUM_PLANNER'])
        }
        self.album_meta['disc_total'] = meta['DATA1']['DATA'][self.album_meta['track_total'] - 1]['ALBUM_CD_NO']

        # Initialize empty lists
        track_ids = []
        track_numbers = []
        disc_numbers = []
        track_artist = []
        # Append required information to their relevant lists
        for track in meta['DATA1']['DATA']:
            track_ids.append(int(track['SONG_ID']))
            track_numbers.append(track['ALBUM_TRACK_NO'])
            disc_numbers.append(track['ALBUM_CD_NO'])
            track_artist.append(track['ARTIST_NAME'])

        # Create ThreadPoolExecutor to handle multiple downloads at once
        with ThreadPoolExecutor(max_workers=int(self.settings['threads'])) as executor:
            executor.map(self._track, track_ids, track_numbers,
                         disc_numbers, track_artist)

    @logger.catch
    def _track(self, id: int, track_number: str, disc_number: str, track_artist: str):
        """Handles the download of a track

        Args:
            id (int): Unique ID of the track
            track_number (str): String representation of the track number
            disc_number (str): String representation of the disc number
            track_artist (str): Name of the artist connected to the track
        """
        meta = self.client.get_stream_meta(id)
        if meta: # Meta can return False if unavailable for stream
            logger.info(f"Track: {unquote(meta['SONG_NAME'])}")
            ext = get_ext(meta['FILE_EXT'])
            file_path = os.path.join(self.album_path, f"{track_number}. {sanitize(unquote(meta['SONG_NAME']))}{ext}")
            if os.path.exists(file_path):
                logger.debug(f"{file_path} already exists.")
            else:
                r = self.client.session.get(unquote(meta['STREAMING_MP3_URL']))
                r.raise_for_status()
                lyrics = self.client.get_timed_lyrics(id)
                if self.settings['timed_lyrics'] == 'Y' and lyrics != None:
                    lyrics = format_genie_lyrics(lyrics)
                try:
                    self._write_track(file_path, r)
                except OSError:
                    # OSError assumes excessive file length, rename file and continue writing
                    file_path = os.path.join(self.album_path, f"{track_number}.{ext}")
                    logger.debug(f"{track_number} has been renamed as it exceeded the maximum length.")
                    self._write_track(file_path, r)
                self._fix_tags(file_path, lyrics, ext, track_number, disc_number,
                            track_artist, unquote(meta['SONG_NAME']))

    @staticmethod
    def _write_track(file_path: str, r: Response):
        """Write track response data to file"""
        with open(file_path, 'wb') as f:
            for chunk in r.iter_content(32 * 1024):
                if chunk:
                    f.write(chunk)

    @logger.catch
    def _fix_tags(self, path: str, lyrics: str, ext: str, track_number: str, disc_number: str, track_artist: str, track_title: str):
        """Fixes I3D/FLAC metadata

        Args:
            path (str): Path of .mp3/.flac file
            lyrics (str): Song lyrics
            ext (str): File extension (.mp3/.flac)
            track_number (str): String representation of the track number
            disc_number (str): String representation of the disc number
            track_artist (str): Name of the artist connected to the track
            track_title (str): Name of the track
        """
        if ext == ".mp3":
            # Instantiate ID3 object
            try:
                audio = id3.ID3(path)
            except id3.ID3NoHeaderError:
                audio = id3.ID3()
            # Append necessary tags
            audio['TIT2'] = id3.TIT2(text=str(track_title))
            audio['TALB'] = id3.TALB(text=str(self.album_meta['album_title']))
            audio['TCON'] = id3.TCON(text=str(self.album_meta['album_title']))
            audio['TRCK'] = id3.TRCK(text=str(track_number) + "/" + str(self.album_meta['track_total']))
            audio['TPOS'] = id3.TPOS(text=str(disc_number) + "/" + str(self.album_meta['disc_total']))
            audio['TDRC'] = id3.TDRC(text=self.album_meta['release_date'])
            audio['TPUB'] = id3.TPUB(text=self.album_meta['planning'])
            audio['TPE1'] = id3.TPE1(text=unquote(track_artist))
            audio['TPE2'] = id3.TPE2(text=self.album_meta['album_artist'])
            if lyrics != None:
                audio['USLT'] = id3.USLT(text=lyrics)
            audio.save(path, "v2_version=3") # Write file
        else:
            audio = FLAC(path)
            # Append necessary tags
            audio['TRACKTOTAL'] = str(self.album_meta['track_total'])
            audio['DISCTOTAL'] = str(self.album_meta['disc_total'])
            audio['DATE'] = self.album_meta['release_date']
            audio['LABEL'] = self.album_meta['planning']
            audio['ARTIST'] = unquote(track_artist)
            audio['ALBUMARTIST'] = self.album_meta['album_artist']
            if lyrics != None:
                audio['LYRICS'] = lyrics
            audio.save()  # Write file

    def _download_cover(self, url: str):
        """Download cover artwork"""
        path = os.path.join(self.album_path, 'cover.jpg')
        if not os.path.isfile(path):
            r = self.client.session.get(unquote(url))
            with open(path, 'wb') as f:
                f.write(r.content)
        else:
            logger.debug(f"{path} already exists.")

    def _collect(self, type: str, id: int):
        """Returns metadata for specified release"""
        if type == 'artist':
            return self.client.get_artist_albums(id)
        if type == 'album':
            return self.client.get_album(id)
