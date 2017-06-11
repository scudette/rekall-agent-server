"""This module provides helpers for the Web2py DAL."""
import json

from gluon.dal import SQLCustomType
from rekall_lib import serializer
from rekall_lib import utils


def SerializerType(cls):
    if utils.issubclass(cls, serializer.SerializedObject):
        pass

    elif isinstance(cls, basestring):
        cls = serializer.SerializedObject.classes.get(cls)
        if cls is None:
            raise TypeError("Unable to find constructor for %s" % cls)

    else:
        raise TypeError("Must provide an instance of SerializedObject.")

    def encode(x):
        if not isinstance(x, cls):
            raise TypeError("Can only store objects of type %s" % cls)
        return x.to_json()

    def decode(x):
        if not x:
            data = dict(__type__=cls.__name__)
        else:
            data = json.loads(x)

        return serializer.unserialize(data , strict_parsing=False)

    return SQLCustomType(
        type='text',
        native='text',
        encoder=encode,
        decoder=decode)
