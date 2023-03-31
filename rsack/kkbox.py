import os
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4
from loguru import logger
from concurrent.futures import ThreadPoolExecutor

from rsack.clients.kkbox import KkboxAPI
from rsack.utils import Settings, sanitize

class Download():
    def __init__(self, url):
        self.settings = Settings().KKBox()
        self.id = url.split("/")[-1]
        self.client = KkboxAPI(proxy=self.settings['proxy'])
        self.client.login(email=self.settings['email'],
                            password=self.settings['password'],
                            region_bypass=False)
        if url.split("/")[-2] == "artist":
            artist = self.client.get_artist(self.id)
            artist_raw_id = artist["profile"]["artist_id"]
            artist_albums = self.client.get_artist_albums(artist_raw_id,20,0)
            for album in artist_albums:
                self._download_album(album['encrypted_album_id'])
        else:
            self._download_album(self.id)

    @staticmethod
    def _determine_type(audio_quality: str) -> str:
        """Return name of stream data given the audio quality
        """
        legend = {
            '128k': 'mp3_128k_chromecast',
            '192k': 'mp3_192k_kkdrm1',
            '320k': 'aac_320k_m4a_kkdrm1',
            'hifi': 'flac_16_download_kkdrm',
            'hires': 'flac_24_download_kkdrm',
        }
        return legend[audio_quality]
    
    def get_img_url(self, url_template, size, file_type='jpg'):
        url = url_template
        # not using .format() here because of possible data leak vulnerabilities
        if size > 2048:
            url = url.replace('fit/{width}x{height}', 'original')
            url = url.replace('cropresize/{width}x{height}', 'original')
        else:
            url = url.replace('{width}', str(size))
            url = url.replace('{height}', str(size))
        url = url.replace('{format}', file_type)
        return url
    
    @logger.catch
    def _template(self):
        keys = {
            "artist": self.meta['album']['artist_name'],
            "title": self.meta['album']['album_name'],
            "date": self.meta['release_date'],
            "album_id": str(self.meta['album']['album_id']),
            "encrypted_album_id": self.meta['album']['encrypted_album_id'],
            "artist_id": str(self.meta['album']['artist_id']),
            "encrypted_artist_id": self.meta['album']['encrypted_artist_id']
        }
        template = self.settings['template']
        for k in keys:
            template = template.replace(f"{{{k}}}", sanitize(keys[k]))
        return template
    
    def _create_album_folder(self):
        self.album_path = self.settings['path'] + self._template()
        try:
            if not os.path.exists(self.album_path):
                os.makedirs(self.album_path)
        except OSError as exc:
            if exc.errno == 36: # Exceeded path limit
                self.album_path = os.path.join(self.settings['path'], 'EDIT ME')
                if not os.path.exists(self.album_path): # Retry
                    os.makedirs(self.album_path)
    
    def _download_cover(self):
        url = self.get_img_url(self.meta['album']['album_photo_info']['url_template'], 3000)
        logger.info("Downloading original artwork")
        r = self.client.s.get(url)
        self.cover_path = os.path.join(self.album_path, 'cover.jpg')
        with open(self.cover_path, 'wb') as f:
            f.write(r.content)
            
        logger.info("Downloading artwork to embed")
        url = self.get_img_url(self.meta['album']['album_photo_info']['url_template'], 600)
        r = self.client.s.get(url)
        self.cover_path_embed = os.path.join(self.album_path, 'embed.jpg')
        with open(self.cover_path_embed, 'wb') as f:
            f.write(r.content)
    
    @logger.catch
    def _download_album(self, id):
        self.meta = self.client.get_album(id=id)
        self.meta['release_date'] = self.meta['album']['album_date'].replace('-', '.')
        # Include first day of month if not present
        if len(self.meta['release_date']) == 7:
            self.meta['release_date'] = self.meta['release_date'] + ".01"
        song_list = self.client.get_album_more(self.meta['album']['album_id'])
        self._create_album_folder()
        self._download_cover()
        self.meta['album']['track_total'] = song_list['song_list']['song'][-1]['trankno'] # Assign track total because the existing 'collected_count' is not accurate.
        with ThreadPoolExecutor(max_workers=int(self.settings['threads'])) as executor:
            executor.map(self._download_track, song_list['song_list']['song'])
        logger.debug(f"Deleting {self.cover_path_embed}")
        os.remove(self.cover_path_embed)
    
    def _format_lyrics(self, lyrics: dict):
        embedded = ''
        synced = ''
        for lyr in lyrics['data']['lyrics']:
            if not lyr['content']:
                embedded += '\n'
                synced += '\n'
                continue

            time = lyr['start_time']
            min = int(time / (1000 * 60))
            sec = int(time / 1000) % 60
            ms = int(time % 100)
            time_tag = f'[{min:02d}:{sec:02d}.{ms:02d}]'

            embedded += lyr['content'] + '\n'
            synced += time_tag + lyr['content'] + '\n'
        return synced
    
    @logger.catch
    def _download_track(self, song: dict):
        id = song['song_more_url'].split('/')[-1]
        urls = self.client.get_ticket(id, "webclient")
        url_type = self._determine_type(song['audio_quality'][-1])
        for u in urls:
            if u['name'] == url_type:
                url = u['url']
        file_ext = f".{url_type.split('_')[0]}"
        if file_ext == '.aac': # Correct .aac to .m4a
            file_ext = '.m4a'
        file_name = sanitize(f"{song['trankno'].zfill(2)}. {song['text']}{file_ext}")
        file_path = os.path.join(self.album_path, file_name)
        if not os.path.exists(file_path):
            logger.info(f"{file_name}")
            self.client.kkdrm_dl(url=url, path=file_path)
            if song['song_lyrics_valid'] == 1:
                l = self.client.get_song_lyrics(id)
                if l['status']['type'] ==  "OK":
                    lyrics = self._format_lyrics(l)
                else:
                    lyrics = ''
            else:
                lyrics = ''
            Tag(file_path=file_path, file_ext=file_ext, track_meta=song, lyrics=lyrics, album_meta=self.meta, cover_path=self.cover_path_embed)
        else:
            logger.info(f"Already exists: {file_path}")
            
class Tag():
    def __init__(self, file_path: str, file_ext: str, track_meta: dict, lyrics: str, album_meta: dict, cover_path: str):
        self.cover_path = cover_path
        self.file_path = file_path
        self.album_meta = album_meta
        self.track_meta = track_meta
        self.lyrics = lyrics
        if file_ext == ".flac":
            self.flac()
        elif file_ext == '.m4a':
            self.aac()
    
    @logger.catch
    def aac(self):
        audio = MP4(self.file_path)

        # Tags
        logger.debug(f"Writing tags to {self.file_path}")
        audio['\xa9ART'] = self.track_meta['artist_role']['mainartist_list']['mainartist']
        audio['aART'] = self.album_meta['album']['artist_name'] # Look into this
        audio['\xa9alb'] = self.album_meta['album']['album_name']
        audio['\xa9nam'] = self.track_meta['text']
        audio['\xa9cmt'] = self.track_meta['song_id']
        audio['\xa9gen'] = self.track_meta['genre_name']
        audio['trkn'] = [(int(self.track_meta['trankno']), int(self.album_meta['album']['track_total']))]
        audio['disk'] = [(1, 1)] # KKBOX don't include disc numbers
        audio['\xa9day'] = self.album_meta['release_date']
        
        audio.save()
        
    @logger.catch
    def flac(self):
        """Tag flac file
        """
        audio = FLAC(self.file_path) # Initialize FLAC object.
        
        # Remove replay gain tags
        audio.pop('replaygain_track_peak')
        audio.pop('replaygain_album_gain')
        audio.pop('replaygain_track_gain')
        audio.pop('replaygain_album_peak')
        audio.pop('replaygain_reference_loudness')

        # Embed cover artwork
        audio_image = Picture()
        audio_image.type = 3
        audio_image.desc = 'Front Cover'
        with open(self.cover_path, 'rb') as f:
            audio_image.data = f.read()
        audio.add_picture(audio_image)
        
        # Tags
        logger.debug(f"Writing tags to {self.file_path}")
        audio['ARTIST'] = self.track_meta['artist_role']['mainartist_list']['mainartist']
        audio['ALBUMARTIST'] = self.album_meta['album']['artist_name'] # Look into this
        audio['ALBUM'] = self.album_meta['album']['album_name']
        audio['TITLE'] = self.track_meta['text']
        audio['COMMENT'] = self.track_meta['song_id']
        audio['GENRE'] = self.track_meta['genre_name']
        audio['TRACKNUMBER'] = self.track_meta['trankno']
        audio['TRACKTOTAL'] = str(self.album_meta['album']['track_total'])
        audio['DISCTOTAL'] = "1" # KKBOX don't include disc totals
        audio['DISCNUMBER'] = "1" # KKBOX don't include disc numbers
        audio['DATE'] = self.album_meta['release_date']
        
        if self.lyrics != '':
            audio['LYRICS'] = self.lyrics
                
        # Save file
        audio.save()