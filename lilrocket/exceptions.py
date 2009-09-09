class LilRocketError(Exception):
class MissingDependency(LilRocketError): pass
class ConfigFilePathNotFound(LilRocketError): pass
class WhooshError(LilRocketError): pass
