import os
import mutagen.id3 as id3
from loguru import logger
from urllib.parse import unquote
from mutagen.flac import FLAC
from rsack.clients import genie
from rsack.utils import Settings, format_genie_lyrics, get_ext, sanitize, format_genie_lyrics
from concurrent.futures import ThreadPoolExecutor

class Download:
    def __init__(self, type, id):
        self.settings = Settings().Genie()
        self.client = genie.Client()
        self.client.auth(
            username=self.settings['username'], password=self.settings['password'])
        self.meta = self._collect(type, id)
        if type == "artist":
            self._artist(id)
        elif type == "album":
            self._album(id)

    def _artist(self, id):
        """Iterate albums in the artists album list

        Args:
            id (int): Artist UID

        Note:
            Artist album lists do not contain any track information so a POST to song/j_AlbumSongList.json is still necessary.
            Perhaps self.meta['artist_song_list'] could be utilized
        """
        for album in self.meta['DataSet']['DATA']:
            self._album(album['ALBUM_ID'])

    @logger.catch
    def _album(self, id):
        """Iterate tracks in the album list

        Args:
            id (int): Album UID
        """
        meta = self.client.get_album(id)
        logger.info(
            f"Album: {unquote(meta['DATA0']['DATA'][0]['ALBUM_NAME'])}")
        artist_name = sanitize(
            unquote(meta['DATA0']['DATA'][0]['ARTIST_NAME']))
        if self.settings['artist_folders'].upper() == 'Y':
            self.album_path = os.path.join(
                self.settings['path'], artist_name, f"{artist_name} - {sanitize(unquote(meta['DATA0']['DATA'][0]['ALBUM_NAME']))}")
        else:
            self.album_path = os.path.join(
                self.settings['path'], f"{artist_name} - {sanitize(unquote(meta['DATA0']['DATA'][0]['ALBUM_NAME']))}")
        if not os.path.isdir(self.album_path):
            os.makedirs(self.album_path)
        self._download_cover(
            unquote(meta['DATA0']['DATA'][0]['ALBUM_IMG_PATH_600']))

        # Create dict containing relevant album information for tagging.
        self.f_meta = {
            "album_title": meta['DATA0']['DATA'][0]['ALBUM_NAME'],
            "track_total": len(meta['DATA1']['DATA']),
            "album_artist": unquote(meta['DATA0']['DATA'][0]['ARTIST_NAME']),
            "release_date": meta['DATA0']['DATA'][0]['ALBUM_RELEASE_DT'],
            "planning": unquote(meta['DATA0']['DATA'][0]['ALBUM_PLANNER'])
        }
        self.f_meta['disc_total'] = meta['DATA1']['DATA'][self.f_meta['track_total'] - 1]['ALBUM_CD_NO']

        tracks = []
        track_numbers = []
        disc_numbers = []
        track_artist = []
        for track in meta['DATA1']['DATA']:
            tracks.append(track['SONG_ID'])
            track_numbers.append(track['ALBUM_TRACK_NO'])
            disc_numbers.append(track['ALBUM_CD_NO'])
            track_artist.append(track['ARTIST_NAME'])

        logger.info(f"Threads: {self.settings['threads']}")
        with ThreadPoolExecutor(max_workers=int(self.settings['threads'])) as executor:
            executor.map(self._track, tracks, track_numbers,
                         disc_numbers, track_artist)

    @logger.catch
    def _track(self, id, track_number, disc_number, track_artist):
        meta = self.client.get_stream_meta(id, '24bit')
        logger.info(f"Track: {unquote(meta['SONG_NAME'])}")
        ext = get_ext(meta['FILE_EXT'])
        file_path = os.path.join(
            self.album_path, f"{track_number}. {sanitize(unquote(meta['SONG_NAME']))}.{ext}")
        r = self.client.session.get(unquote(meta['STREAMING_MP3_URL']))
        r.raise_for_status()
        # Retrieve lyrics
        lyrics = self.client.get_timed_lyrics(id)
        if self.settings['timed_lyrics'] == 'Y' and lyrics != None:
            lyrics = format_genie_lyrics(lyrics)
        if os.path.exists(file_path):
            logger.debug(f"{file_path} already exists.")
        else:
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(32 * 1024):
                    if chunk:
                        f.write(chunk)
            self._fix_tags(file_path, lyrics, ext, track_number, disc_number,
                        track_artist, unquote(meta['SONG_NAME']))

    @logger.catch
    def _fix_tags(self, path, lyrics, ext, track_number, disc_number, track_artist, track_title):
        if ext == "mp3":
            try:
                audio = id3.ID3(path)
            except id3.ID3NoHeaderError:
                audio = id3.ID3()
            audio['TIT2'] = id3.TIT2(text=str(track_title))
            audio['TALB'] = id3.TALB(text=str(self.f_meta['album_title']))
            audio['TCON'] = id3.TCON(text=str(self.f_meta['album_title']))
            audio['TRCK'] = id3.TRCK(
                text=str(track_number) + "/" + str(self.f_meta['track_total']))
            audio['TPOS'] = id3.TPOS(
                text=str(disc_number) + "/" + str(self.f_meta['disc_total']))
            audio['TDRC'] = id3.TDRC(text=self.f_meta['release_date'])
            audio['TPUB'] = id3.TPUB(text=self.f_meta['planning'])
            audio['TPE1'] = id3.TPE1(text=unquote(track_artist))
            audio['TPE2'] = id3.TPE2(text=self.f_meta['album_artist'])
            if lyrics != None:
                audio['USLT'] = id3.USLT(text=lyrics)
            audio.save(path, "v2_version=3")
        else:
            audio = FLAC(path)
            audio['TRACKTOTAL'] = str(self.f_meta['track_total'])
            audio['DISCTOTAL'] = str(self.f_meta['disc_total'])
            audio['DATE'] = self.f_meta['release_date']
            audio['LABEL'] = self.f_meta['planning']
            audio['ARTIST'] = unquote(track_artist)
            audio['ALBUMARTIST'] = self.f_meta['album_artist']
            if lyrics != None:
                audio['LYRICS'] = lyrics
            audio.save()

    def _download_cover(self, url):
        path = os.path.join(self.album_path, 'cover.jpg')
        if not os.path.isfile(path):
            r = self.client.session.get(unquote(url))
            with open(path, 'wb') as f:
                f.write(r.content)
        else:
            logger.debug(f"{path} already exists.")

    def _collect(self, type, id):
        """Returns metadata for specified release

        Args:
            type (str): Release type (album/artist)
            id (int): Artist or Album UID

        Returns:
            [dict]: API response
        """
        if type == 'artist':
            return self.client.get_artist(id)
        if type == 'album':
            return self.client.get_album(id)
