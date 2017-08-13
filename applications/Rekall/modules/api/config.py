"""Determine the server configuration."""
import os
import yaml

from rekall_lib import serializer


class ServerConfig(serializer.SerializedObject):
    schema = [
        dict(name="demo", type="bool",
             doc="If set, this installation is a demo installation.")
    ]


_CONFIG = None



def GetConfig(current):
    yaml_path = os.path.join(
        current.request.folder, "private", "server_config.yaml")
    global _CONFIG
    if _CONFIG is None:
        try:
            _CONFIG = serializer.unserialize(
                yaml.load(open(yaml_path).read()),
                strict_parsing=True,
                type=ServerConfig)
        except (IOError, ValueError):
            # File does not exist, we just make an empty one.
            _CONFIG = ServerConfig()

    return _CONFIG
