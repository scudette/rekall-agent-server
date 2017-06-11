from api import users
from api import types
from api import dal


db.define_table('permissions',
                Field('resource'),
                Field('role', requires=IS_IN_SET(users.roles)),
                Field('user'),
                Field('conditions', type=dal.SerializerType(
                    types.IAMCondition)))
