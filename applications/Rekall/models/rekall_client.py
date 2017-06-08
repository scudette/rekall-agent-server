import datetime

db.define_table('clients',
                Field('client_id', unique=True),

                # These can be searched server side.
                Field('hostname',
                      comment="The FQDN of the client"),
                Field('users',
                      comment="A comma separated list of users."),

                # Search using time: operator.
                Field('last', type="datetime",
                      comment="Last contact time"),

                # Information here is searchable in the browser.
                Field('summary', type='json',
                      comment='A client.StartupMessage instance '
                      'filled in by the client'),

                format='%(client_id)s')

# TODO: Implement log retention mechanism.
db.define_table('client_logs',
                # Insertion time.
                Field('timestamp', type="datetime",
                      default=datetime.datetime.utcnow),
                Field('client_id',
                      comment='The client id the event came from.'),
                Field('event',
                      comment='Type of interaction (e.g. startup)'),
                Field('data', type='json',
                      comment='Additional information about the event'),
                )

db.define_table('flows',
                Field('flow_id', unique=True, notnull=True,
                      comment="Each flow has a unique ID"),
                Field('client_id', notnull=True,
                      comment="The Client this flow is intended for."),
                Field('timestamp', type="datetime",
                      default=datetime.datetime.utcnow,
                      comment="When the flow was created"),
                Field('state', default='scheduled',
                      comment='Current state of the flow'),
                Field('flow', type='json',
                      comment="Flow to be sent to the client."),
                Field('creator', type='string',
                      comment="Username that created the flow"),
                Field('status', type='json',
                      comment="The latest Flow status."),
                )

db.define_table('collections',
                Field('collection_id', unique=True, notnull=True,
                      comment="Each collection has a unique ID"),
                Field('flow_id', notnull=True,
                      comment="The flow that owns this collection"),
                Field('part', type='integer',
                      comment="The part number of this collection."),
                Field('blob_key',
                      comment="Blob key for this part"),
                Field('gs_object_name'),
                Field('total_rows', type='integer',
                      comment="Total number of rows in this collection"))

db.define_table("uploads",
                Field("blob_key",
                      comment="Blob key for this upload"),
                Field("state",
                      comment="State of this upload (pending, "
                      "received, finalized)"),
                Field("hash",
                      comment="Hash is calculated by the server in a task"),
                Field("fileinfo_id", type='integer'))

db.define_table("upload_files",
                Field("file_information", type='json',
                      comment="FileInformation object for the uploaded file."),
                Field("upload_id", type="integer",
                      comment="ID of upload in the uploads table"),
                Field("flow_id", comment="Flow which owns this upload."),
                )


from gluon import current
current.auth = auth
current.db = db
