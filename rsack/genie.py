import os
import mutagen.id3 as id3
from loguru import logger
from urllib.parse import unquote
from mutagen.flac import FLAC, Picture
from concurrent.futures import ThreadPoolExecutor
from requests.models import Response

from rsack.clients import genie
from rsack.utils import Settings, contribution_check, format_genie_lyrics, get_ext, sanitize


class Download:
    def __init__(self, type: str, id: int):
        """Initialize and control the flow of the download"""
        self.settings = Settings().Genie()
        self.client = genie.Client()
        self.client.auth(username=self.settings['username'], password=self.settings['password'])
        logger.info(f"Threads: {self.settings['threads']}")
        if type == "artist":
            self._artist(id)
        elif type == "album":
            self._album(id)

    def _artist(self, id: int):
        """Iterate albums in artist"""
        meta = self.client.get_artist_albums(id)
        for album in meta['DataSet']['DATA']:
            if contribution_check(id, int(album['ARTIST_ID'])):
                if self.settings['contributions'] == "Y":
                    self._album(album['ALBUM_ID'])
                else:
                    logger.debug("Skipping contribution")
            else:
                self._album(album['ALBUM_ID'])


    @logger.catch
    def _album(self, id: int):
        """Iterate tracks in album"""
        self.meta = self.client.get_album(id)
        logger.info(f"Album: {unquote(self.meta['DATA0']['DATA'][0]['ALBUM_NAME'])}")
        artist_name = sanitize(unquote(self.meta['DATA0']['DATA'][0]['ARTIST_NAME']))
        if self.settings['artist_folders'].upper() == 'Y':
            self.album_path = os.path.join(
                self.settings['path'], artist_name, f"{artist_name} - {sanitize(unquote(self.meta['DATA0']['DATA'][0]['ALBUM_NAME']))}")
        else:
            self.album_path = os.path.join(
                self.settings['path'], f"{artist_name} - {sanitize(unquote(self.meta['DATA0']['DATA'][0]['ALBUM_NAME']))}")
        if not os.path.isdir(self.album_path):
            logger.debug(f"Creating: {self.album_path}")
            os.makedirs(self.album_path)
            
        # Create disc directories
        self.disc_total = int(self.meta['DATA1']['DATA'][len(self.meta['DATA1']['DATA']) - 1]['ALBUM_CD_NO'])
        if  self.disc_total > 1:
            for i in range(0, self.disc_total):
                d = os.path.join(self.album_path, f"Disc {i + 1}")
                if not os.path.isdir(d):
                    os.makedirs(d)
                    
        cover_url = unquote(self.meta['DATA0']['DATA'][0]['ALBUM_IMG_PATH_600'])
        if cover_url == "":
            cover_url = unquote(self.meta['DATA0']['DATA'][0]['ALBUM_IMG_PATH'])
        self._download_cover(cover_url)

        # Initialize empty lists
        track_ids = []
        track_numbers = []
        disc_numbers = []
        track_artist = []
        # Append required information to their relevant lists
        for track in self.meta['DATA1']['DATA']:
            track_ids.append(int(track['SONG_ID']))
            track_numbers.append(f"{track['ALBUM_TRACK_NO']}")
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
            if self.disc_total > 1:
                file_path = os.path.join(self.album_path, f"Disc {disc_number}", f"{int(track_number):02d}. {sanitize(unquote(meta['SONG_NAME']))}{ext}")
            else:
                file_path = os.path.join(self.album_path, f"{int(track_number):02d}. {sanitize(unquote(meta['SONG_NAME']))}{ext}")
            if os.path.exists(file_path):
                logger.debug(f"{file_path} already exists.")
            else:
                r = self.client.session.get(unquote(meta['STREAMING_MP3_URL']))
                r.raise_for_status()
                lyrics = self.client.get_timed_lyrics(id)
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
            # Delete pre-embedded artwork
            audio.delall("APIC")
            # Embed existing artwork
            if self.cover_path:
                with open(self.cover_path, 'rb') as cov_obj:
                    audio.add(id3.APIC(3, 'image/jpg', 3, '', cov_obj.read()))
            # Append necessary tags
            audio['TIT2'] = id3.TIT2(text=track_title)
            audio['TALB'] = id3.TALB(text=unquote(self.meta['DATA0']['DATA'][0]['ALBUM_NAME']))
            audio['TCON'] = id3.TCON(text=unquote(self.meta['DATA0']['DATA'][0]['ALBUM_NAME']))
            audio['TRCK'] = id3.TRCK(text=str(track_number) + "/" + str(len(self.meta['DATA1']['DATA'])))
            audio['TPOS'] = id3.TPOS(text=str(disc_number) + "/" + str(self.disc_total))
            audio['TDRC'] = id3.TDRC(text=self.meta['DATA0']['DATA'][0]['ALBUM_RELEASE_DT'])
            audio['TPUB'] = id3.TPUB(text=unquote(self.meta['DATA0']['DATA'][0]['ALBUM_PLANNER']))
            audio['TPE1'] = id3.TPE1(text=unquote(track_artist))
            audio['TPE2'] = id3.TPE2(text=unquote(self.meta['DATA0']['DATA'][0]['ARTIST_NAME']))
            audio['TCON'] = id3.TCON(text="")
            audio.setall("COMM", [id3.COMM(text=[u"지니뮤직"], encoding=id3.Encoding.UTF8)])
            if lyrics != None and self.settings['timed_lyrics'] == 'Y':
                    lyrics = [(v, int(k)) for k, v in lyrics.items()]
                    audio.setall("SYLT", [id3.SYLT(encoding=id3.Encoding.UTF8, lang='eng', format=2, type=1, text=lyrics)])
            logger.debug(f"Writing tags to: {path}")
            audio.save(path, "v2_version=3") # Write file
        else:
            audio = FLAC(path)
            # Delete pre-embedded artwork
            audio.clear_pictures()
            # Embed existing artwork
            if self.cover_path:
                f_image = Picture()
                f_image.type = 3
                f_image.desc = 'Front Cover'
                with open(self.cover_path, 'rb') as f:
                    f_image.data = f.read()
                audio.add_picture(f_image)
            # Append necessary tags
            audio['TRACKNUMBER'] = str(track_number)
            audio['TRACKTOTAL'] = str(len(self.meta['DATA1']['DATA']))
            audio['DISCNUMBER'] = str(disc_number)
            audio['DISCTOTAL'] = str(self.disc_total)
            audio['DATE'] = self.meta['DATA0']['DATA'][0]['ALBUM_RELEASE_DT']
            audio['LABEL'] = self.meta['DATA0']['DATA'][0]['ALBUM_PLANNER']
            audio['ARTIST'] = unquote(track_artist)
            audio['ALBUMARTIST'] = unquote(self.meta['DATA0']['DATA'][0]['ARTIST_NAME'])
            audio['ALBUM'] = unquote(self.meta['DATA0']['DATA'][0]['ALBUM_NAME'])
            audio['TITLE'] = track_title
            audio['COMMENT'] = "지니뮤직"
            if lyrics != None and self.settings['timed_lyrics'] == 'Y':
                audio['LYRICS'] = format_genie_lyrics(lyrics)
            logger.debug(f"Writing tags to: {path}")
            audio.save()  # Write file

    def _download_cover(self, url: str):
        """Download cover artwork"""
        self.cover_path = os.path.join(self.album_path, 'cover.jpg')
        if not os.path.isfile(self.cover_path):
            r = self.client.session.get(unquote(url))
            with open(self.cover_path, 'wb') as f:
                f.write(r.content)
        else:
            logger.debug(f"{self.cover_path} already exists.")