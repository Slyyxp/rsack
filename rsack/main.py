from loguru import logger
from argparse import ArgumentParser

from rsack.version import __version__
from rsack import bugs, genie, qobuz
from rsack.utils import bugs_id, genie_id, Settings

def get_args():
    parser = ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true', dest='version', required=False)
    parser.add_argument('-b', '--bugs', action='store_true', dest="bugs", required=False)
    parser.add_argument('-g', '--genie', action='store_true', dest="genie", required=False)
    parser.add_argument('-q', '--qobuz', action='store_true', dest="qobuz", required=False)
    parser.add_argument('-u', '--url', nargs='*', dest="url", required=False)
    parser.add_argument('-cfg', '--config', action='store_true', dest="config", required=False)
    parser.add_argument('-o', '--open', action='store_true', dest="open", required=False)
    return parser.parse_args()

    
def main():
    args = get_args()
    if args.version:
        print(__version__)
    if args.config:
        Settings(check=True)
    if args.bugs:
        for url in args.url:
            id = bugs_id(url)
            if "album" in url:
                bugs.Download(type="album", id=id)
            elif "artist" in url:
                bugs.Download(type="artist", id=id)
            elif "track" in url:
                bugs.Download(type="Single tracks not yet available", id=id)
    elif args.genie:
        for url in args.url:
            match = genie_id(url)
            if match.group(1) == "artistInfo":
                type = "artist"
            elif match.group(1) == "albumInfo":
                type = "album"
            else: # Catch invalid info types
                logger.critical("URL type unkown")
            genie.Download(type=type, id=int(match.group(2)))
    elif args.qobuz:
        for url in args.url:
            qobuz.Download(url)