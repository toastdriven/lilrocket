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


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class LilRocket(object):
    def __init__(self, config_filepath=None):
        self.log = logging.getLogger('lilrocket')
        self.config_filepath = config_filepath
        
        # Defaults.
        self.port = 9000
        self.listeners = 5
        self.data_path = os.path.join('var', 'lilrocket', 'data')
        self.index_name = 'default'
        self.spelling_support = True
        self.faceting_support = True
    
    def serve(self):
        # DRL_FIXME: Add a server pid as a guard against multiple servers
        #            working on the saem data.
        pass


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Usage: lilrocket.py /path/to/lilrocket.conf"
        sys.exit(1)
    
    config_filepath = sys.argv[1]
    rocket = LilRocket(config_filepath)
    rocket.serve()
