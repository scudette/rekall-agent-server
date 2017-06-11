# The following serialiable types are only used within the server application.

from rekall_lib import serializer


class IAMCondition(serializer.SerializedObject):
    """Conditions which should be applied on the binding."""
    schema = [
        dict(name="valid_until", type="epoch",
             doc="If set, the binding expires at this date. "
             "Note that once expired it will be removed from the database."),

        dict(name="valid_after", type="epoch",
             doc="If set, the binding applies after this date. "),
    ]
