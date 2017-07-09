import datetime

from api import users
from api import types
from api import dal


db.define_table('permissions',
                Field('resource'),
                Field('role', requires=IS_IN_SET(users.roles)),
                Field('user'),
                Field('conditions', type=dal.SerializerType(
                    types.IAMCondition)))

db.define_table('notifications',
                Field('user'),
                Field("from_user"),
                Field('timestamp', type="datetime",
                      default=datetime.datetime.utcnow),

                # Ensure that messages can not have arbitrary HTML in them. The
                # full message will be expanded by the function
                # rekall.templates.render_message(message_id, args).
                Field('message_id', comment="The message type. Note that "
                      "messages must be one of a small set of templates which "
                      "will be expanded in JS."),

                Field('args', type=dal.JSONType),
                Field('read', type='boolean', default=False))

db.define_table('tokens',
                Field('token_id'),
                Field('delegator'),
                Field('role'),
                Field('resource'),
                Field('expires', type="datetime",
                      default=lambda: (datetime.datetime.utcnow() +
                                       datetime.timedelta(hours=1))))
