from lilrocket.exceptions import ConfigFilePathNotFound
try:
    import json
except ImportError:
    import simplejson as json


class Config(object):
    def __init__(self, config_filepath):
        # Defaults.
        self.port = 9000
        self.listeners = 5
        self.data_path = os.path.join('var', 'lilrocket', 'data')
        self.index_name = 'default'
        self.spelling_support = True
        self.faceting_support = True
        self.config_filepath = config_filepath
    
    def load_configuration(self):
        if not self.config_filepath:
            raise ConfigFilePathNotFound("Path to config file '%s' doesn't seem to exist!" % self.config_filepath)
        
        
