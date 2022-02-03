from loguru import logger
from argparse import ArgumentParser

from rsack import bugs
from rsack.utils import get_id, Settings

def get_args():
    parser = ArgumentParser()
    parser.add_argument('-b', '--bugs', action='store_true', dest="bugs", required=False)
    parser.add_argument('-u', '--url', nargs='*', dest="url", required=False)
    parser.add_argument('-cfg', '--config', action='store_true', dest="config", required=False)
    parser.add_argument('-o', '--open', action='store_true', dest="open", required=False)
    return parser.parse_args()

    
def main():
    args = get_args()
    if args.config:
            Settings(check=True)
    if args.bugs:
        for url in args.url:
            id = get_id(url)
            if "album" in url:
                bugs.Download(type="album", id=id)
            elif "artist" in url:
                logger.critical("Artist batching not yet available")
            elif "track" in url:
                bugs.Download(type="Single tracks not yet available", id=id)
