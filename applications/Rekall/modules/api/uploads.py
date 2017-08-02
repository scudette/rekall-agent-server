import json
from api import audit
from api import users

from google.appengine.ext import blobstore
from gluon import html


def list(current, flow_id):
    uploads = []
    db = current.db
    if flow_id:
        for row in db(db.upload_files.flow_id == flow_id).select():
            uploads.append(dict(
                file_information=json.loads(row.file_information),
                upload_id=row.upload_id))

    return dict(data=uploads)


def download(current, upload_id, filename=None):
    db = current.db
    response = current.response
    if filename is None:
        filename = "download_" + upload_id

    row = db(db.uploads.id == upload_id).select().first()
    if row:
        response.headers[blobstore.BLOB_KEY_HEADER] = row.blob_key
        response.headers["Content-Type"] = "application/octet-stream"
        response.headers["Content-Disposition"] = (
            'attachment; filename="%s"' % html.xmlescape(filename))

        audit.log(current, "FileDownload", upload_id=upload_id)

    else:
        raise ValueError("not found")


def require_uploads_access(current):
    """Determine if the user has access to the uploaded file."""
    db = current.db
    upload_id = current.request.vars.upload_id
    if upload_id:
        for row in db(db.upload_files.upload_id == upload_id).select():
            # User has client approval?
            resource = "/" + row.client_id
            if users.check_permission(current, "clients.view", resource):
                return True

            # Does the user have a hunt approval?
            if row.flow_id.startswith("H"):
                resource = "/" + row.flow_id
                if users.check_permission(current, "hunts.view", resource):
                    return True

    raise users.PermissionDenied()
