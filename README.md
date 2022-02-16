
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


## Example Usage
```
rsack --bugs --url "https://music.bugs.co.kr/album/4070269"
rsack --genie --url "https://genie.co.kr/detail/albumInfo?axnm=82529386"
rsack --qobuz --url "https://play.qobuz.com/album/pby9ir4znxqxc"
```

# rsack_settings.ini
`rsack_settings.ini` can be located in your home folder.
