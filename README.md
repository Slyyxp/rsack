
<p align="center">
  <img src="https://ptpimg.me/5502wc.gif">
</p>


# Installation
```
pip install rsack
```

# Features
## Bugs
- FLAC16, 320kbps
- Timed lyrics
- Artist batching
- Extensive tagging
- Concurrent downloads

## Genie
- FLAC24, FLAC16, 320kbps
- Artist batching
- Extensive tagging
- Concurrent downloads

## Qobuz
- FLAC24, FLAC16
- Artist batching
- Reliant on [qobuz_dl](https://github.com/vitiko98/qobuz-dl) by [vikito98](https://github.com/vitiko98) until further notice.


# Example Usage
```
rsack --bugs --url "https://music.bugs.co.kr/album/4070269"
rsack --genie --url "https://genie.co.kr/detail/albumInfo?axnm=82529386"
rsack --qobuz --url "https://play.qobuz.com/album/pby9ir4znxqxc"
```

# rsack_settings.ini
`rsack_settings.ini` can be located in your home folder.

# Wiki
[Command Usage](https://github.com/Slyyxp/rsack/wiki/Command-Usage)  
[Example Configuration](https://github.com/Slyyxp/rsack/wiki/Configuration)  
[Account Creation](https://github.com/Slyyxp/rsack/wiki/Account-Creation)  

# Accessing clients
Retrieving API data using rsack is rather simple.
```python
from rsack.clients import bugs

client = bugs.Client() # Initialize client object
client.auth(username='', password='') # Authorize user

artist_response = client.get_meta(type='artist', id=80219706) # Make call for artist information using artist UID
album_response = client.get_meta(type='album', id=4071297) # Make call for album information using album UID
track_response = client.get_meta(type='track', id=6147328) # Make call for track information using track UID
```
```python
from rsack.clients import genie

client = genie.Client() # Initialize client object
client.auth(username="", password="") # Authorize user

album = client.get_album(82525503) # Make call for album information using album UID
artist = client.get_artist(80006273) # Make call for artist information using artist UID
track = client.get_stream_meta(95970973) # Make call for stream information using track UID
```
