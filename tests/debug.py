import logging
import os


def init():
    if os.environ.get('IPTREE_DEBUG'):
        logger = logging.getLogger('iptree')
        logger.setLevel(logging.INFO)

        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        logger.addHandler(console)
