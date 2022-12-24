from loguru import logger
from argparse import ArgumentParser
from urllib.parse import urlparse

from rsack.version import __version__
from rsack import bugs, genie, kkbox
from rsack.utils import Settings, bugs_id, genie_id

def get_args():
    """Generate arguments"""
    parser = ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true', dest='version', required=False)
    parser.add_argument('-u', '--url', nargs='*', dest="url", required=False)
    return parser.parse_args()

def main():
    """Entry point"""
    args = get_args()
    if args.version:
        print(__version__)
    if args.url:
        for url in args.url:
            domain = urlparse(url).netloc.replace("www.", "")
            if domain == "music.bugs.co.kr":
                id = bugs_id(url)
                if "album" in url:
                    bugs.Download(type="album", id=int(id))
                elif "artist" in url:
                    bugs.Download(type="artist", id=int(id))
                elif "track" in url:
                    bugs.Download(type="Single tracks not yet available", id=int(id))
            elif domain == "genie.co.kr":
                    match = genie_id(url)
                    if match.group(1) == "artistInfo":
                        type = "artist"
                    elif match.group(1) == "albumInfo":
                        type = "album"
                    else: # Catch invalid info types
                        logger.critical("URL type unkown")
                    genie.Download(type=type, id=int(match.group(2)))
            elif domain == "play.kkbox.com" or domain == "kkbox.com":
                kkbox.Download(url)