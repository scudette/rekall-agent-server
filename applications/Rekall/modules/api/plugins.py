import os
import yaml

_RekallAPI = None
_RekallSessionAPI = None

def RekallAPI(current):
    yaml_path = os.path.join(current.request.folder, "private", "api.yaml")
    global _RekallAPI
    if _RekallAPI is None:
        _RekallAPI = {}
        for desc in yaml.load(open(yaml_path).read()):
            _RekallAPI[desc["plugin"]] = desc

    return _RekallAPI


def SessionAPI(current):
    yaml_path = os.path.join(
        current.request.folder, "private", "session_api.yaml")
    global _RekallSessionAPI
    if _RekallSessionAPI is None:
        _RekallSessionAPI = dict(name="session", args={})
        for arg in yaml.load(open(yaml_path).read()):
            _RekallSessionAPI["args"][arg["name"]] = arg

    return _RekallSessionAPI


def list(current):
    """List all available Rekall plugins."""
    return dict(
        data=[{'plugin': x['plugin'],
               'name': x['name'],
              } for x in RekallAPI(current).values()])


def get(current, plugin=None):
    if plugin:
        return RekallAPI(current).get(plugin) or {}
