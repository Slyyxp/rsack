
<p align="center">
  <img src="https://ptpimg.me/5502wc.gif">
</p>

# Features
- Bugs.co.kr support
- Genie.co.kr support
- Batch download artist pages
- FLAC 24/16
- Accessible clients
- Simultaneous track downloads

# Installation
```
pip install rsack
```

## Example Usage
```
rsack --bugs --url "https://music.bugs.co.kr/album/4070269"
rsack -b -u "https://music.bugs.co.kr/album/4070269"
```

# rsack_settings.ini
`rsack_settings.ini` can be located in your home folder.

# Client
```python
from rsack.clients import genie

def information():
    client = genie.Client() # Initialize client object
    client.auth(username="MyUsername", password="MyPassword") # Authorize user
    album = client.get_album(82525503) # Make call for album information using album UID
    artist = client.get_artist(80006273) # Make call for artist information using artist UID
    track = client.get_stream_meta(95970973) # Make call for stream information using track UID
    
if __name__ == "__main__":
    information()
```
