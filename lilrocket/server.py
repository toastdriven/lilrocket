# -*- coding: utf-8 -*-
import logging
import os
import Queue
import sys
import threading

try:
    import json
except ImportError:
    import simplejson as json

# Need to try-except this?
import whoosh


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Configuration defaults. Everything on by default.
PORT = 9000
LISTENERS = 5
DATA_PATH = os.path.join('var', 'lilrocket', 'data')
INDEX_NAME = 'default'
SPELLING_SUPPORT = True
FACETING_SUPPORT = True


class LilRocket(object):
    def __init__(self):
        self.log = logging.getLogger('lilrocket')
    

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Usage: lilrocket.py /path/to/lilrocket.conf"
        sys.exit(1)
    
    conf_filepath = sys.argv[1]
    rocket = LilRocket(conf_filepath)
    rocket.serve()
