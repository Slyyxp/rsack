![GitHub last commit](https://img.shields.io/github/last-commit/Slyyxp/rsack) ![GitHub repo size](https://img.shields.io/github/repo-size/Slyyxp/rsack) ![GitHub](https://img.shields.io/github/license/Slyyxp/rsack) ![PyPI - Downloads](https://img.shields.io/pypi/dm/rsack) ![GitHub closed issues](https://img.shields.io/github/issues-closed-raw/Slyyxp/rsack) ![GitHub issues](https://img.shields.io/github/issues-raw/Slyyxp/rsack)

# Installation
```bash
pip install rsack
```

## Alternatively..
```bash
git clone https://github.com/Slyyxp/rsack.git
cd rsack
python setup.py install
```

# Features
## Bugs
- FLAC16, 320kbps
- Timed lyrics
- Artist batching
- Extensive tagging
- Concurrent downloads
- Client utlizing undocumented mobile API.

## Genie
- FLAC24, FLAC16, 320kbps
- Artist batching
- Timed lyrics
- Extensive tagging
- Concurrent downloads
- Client utlizing undocumented mobile API.

# rsack_settings.ini
`rsack_settings.ini` can be located in your home folder.

# Wiki
[Command Usage](https://github.com/Slyyxp/rsack/wiki/Command-Usage)  
[Example Configuration](https://github.com/Slyyxp/rsack/wiki/Configuration)  
[Account Creation](https://github.com/Slyyxp/rsack/wiki/Account-Creation)  

# Retrieving API Data
```python
from rsack.clients import bugs

client = bugs.Client() # Initialize client object
client.auth(username='', password='') # Authorize user

artist = client.get_artist(id=80219706) # Make call for artist information using artist UID
album = client.get_album(id=4071297) # Make call for album information using album UID
track = client.get_track(id=6147328) # Make call for track information using track UID
```
```python
from rsack.clients import genie

client = genie.Client() # Initialize client object
client.auth(username="", password="") # Authorize user

album = client.get_album(82525503) # Make call for album information using album UID
artist = client.get_artist(80006273) # Make call for artist information using artist UID
track = client.get_stream_meta(95970973) # Make call for stream information using track UID
```
# FAQ
### Why Are Downloads Slow?
Servers for both Bugs and Genie are located in Korea, if you are outside of Asia downloads will likely be somewhat slow.

## Bugs
### Can I Download Music Videos?
No you cannot, these files are not streamable.
### Does Bugs Have Hi-Res?
Bugs does not offer any 24bit files at the time of writing this.

## Genie
### Which Streaming Pass Do I Need?
KT offer a 24bit package, beyond that i'm not sure.  
https://product.kt.com/wDic/productDetail.do?ItemCode=1282
