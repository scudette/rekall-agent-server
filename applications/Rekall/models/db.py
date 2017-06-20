# -*- coding: utf-8 -*-

# -------------------------------------------------------------------------
# This scaffolding model makes your app work on Google App Engine too
# File is released under public domain and you can use without limitations
# -------------------------------------------------------------------------
from gluon.globals import current
import datetime

from api import dal
from rekall_lib.types import agent
from rekall_lib.types import artifacts


if request.global_settings.web2py_version < "2.14.1":
    raise HTTP(500, "Requires web2py 2.13.3 or newer")

# -------------------------------------------------------------------------
# if SSL/HTTPS is properly configured and you want all HTTP requests to
# be redirected to HTTPS, uncomment the line below:
# -------------------------------------------------------------------------
# request.requires_https()

# -------------------------------------------------------------------------
# app configuration made easy. Look inside private/appconfig.ini
# -------------------------------------------------------------------------
from gluon.contrib.appconfig import AppConfig

# -------------------------------------------------------------------------
# once in production, remove reload=True to gain full speed
# -------------------------------------------------------------------------
myconf = AppConfig(reload=True)

if not request.env.web2py_runtime_gae:
    # ---------------------------------------------------------------------
    # if NOT running on Google App Engine use SQLite or other DB
    # ---------------------------------------------------------------------
    db = DAL(myconf.get('db.uri'),
             pool_size=myconf.get('db.pool_size'),
             migrate_enabled=myconf.get('db.migrate'),
             check_reserved=['all'])
else:
    # ---------------------------------------------------------------------
    # connect to Google BigTable (optional 'google:datastore://namespace')
    # ---------------------------------------------------------------------
    db = DAL('google:datastore+ndb')
    # ---------------------------------------------------------------------
    # store sessions and tickets there
    # ---------------------------------------------------------------------
    session.connect(request, response, db=db)
    # ---------------------------------------------------------------------
    # or store session in Memcache, Redis, etc.
    # from gluon.contrib.memdb import MEMDB
    # from google.appengine.api.memcache import Client
    # session.connect(request, response, db = MEMDB(Client()))
    # ---------------------------------------------------------------------

# -------------------------------------------------------------------------
# by default give a view/generic.extension to all actions from localhost
# none otherwise. a pattern can be 'controller/function.extension'
# -------------------------------------------------------------------------
response.generic_patterns = ['*'] if request.is_local else []


# -------------------------------------------------------------------------
# choose a style for forms
# -------------------------------------------------------------------------
response.formstyle = myconf.get('forms.formstyle')  # or 'bootstrap3_stacked' or 'bootstrap2' or other
response.form_label_separator = myconf.get('forms.separator') or ''

# -------------------------------------------------------------------------
# (optional) optimize handling of static files
# -------------------------------------------------------------------------
# response.optimize_css = 'concat,minify,inline'
# response.optimize_js = 'concat,minify,inline'

# -------------------------------------------------------------------------
# (optional) static assets folder versioning
# -------------------------------------------------------------------------
# response.static_version = '0.0.0'

# -------------------------------------------------------------------------
# Here is sample code if you need for
# - email capabilities
# - authentication (registration, login, logout, ... )
# - authorization (role based authorization)
# - services (xml, csv, json, xmlrpc, jsonrpc, amf, rss)
# - old style crud actions
# (more options discussed in gluon/tools.py)
# -------------------------------------------------------------------------

# -------------------------------------------------------------------------
# Define your tables below (or better in another model file) for example
#
# >>> db.define_table('mytable', Field('myfield', 'string'))
#
# Fields can be 'string','text','password','integer','double','boolean'
#       'date','time','datetime','blob','upload', 'reference TABLENAME'
# There is an implicit 'id integer autoincrement' field
# Consult manual for more options, validators, etc.
#
# More API examples for controllers:
#
# >>> db.mytable.insert(myfield='value')
# >>> rows = db(db.mytable.myfield == 'value').select(db.mytable.ALL)
# >>> for row in rows: print row.id, row.myfield
# -------------------------------------------------------------------------

# -------------------------------------------------------------------------
# after defining tables, uncomment below to enable auditing
# -------------------------------------------------------------------------
# auth.enable_record_versioning(db)

# Make db available through the current global variable.
current.db = db


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
                Field('flow', type=dal.SerializerType(agent.Flow),
                      comment="Flow to be sent to the client."),
                Field('creator', type='string',
                      comment="Username that created the flow"),
                Field('status', type=dal.SerializerType(agent.FlowStatus),
                      comment="The latest Flow status."),
                )

db.define_table('collections',
                Field('collection_id', unique=True, notnull=True,
                      comment="Each collection has a unique ID"),
                Field('client_id',
                      comment="The client which uploaded this collection."),
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


db.define_table("artifacts",
                Field("name", unique=True, notnull=True,
                      comment="The unique name of the artifact."),
                Field("artifact", type=dal.SerializerType(artifacts.Artifact),
                      comment="The name of the artifact."),
                Field("artifact_text",
                      comment="The raw text of the artifact."),

                )

db.define_table("canned_flows",
                Field("name", unique=True, notnull=True,
                      comment="The unique name of the canned flow"),
                Field("description",
                      comment="A description of the canned flow"),
                Field("category",
                      comment="A category for this canned flow"),
                Field("flow", type=dal.SerializerType(agent.CannedFlow),
                      comment="The canned flow"),
                )
