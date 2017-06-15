"""Get information about collections."""
from gluon import http

from google.appengine.ext import blobstore


def metadata(current, collection_id):
    db = current.db
    if collection_id:
        collection_row = db(
            db.collections.collection_id == collection_id).select().first()
        if collection_row:
            flow_id = collection_row.flow_id
            flow_row = db(db.flows.flow_id == flow_id).select().first()
            if flow_row:
                return dict(flow=flow_row.flow.to_primitive(),
                            status=flow_row.status.to_primitive())

    return {}


def get(current, collection_id, client_id, part):
    """Stream the requested collection.

    Note that we do not edit the collection in any way we just stream the same
    thing the client sent to us. We rely on AppEngine's automatic blob store
    detection to stream the data from blob store by setting the right header in
    the response.
    """
    db = current.db
    response = current.response
    part = int(part)

    row = db(db.collections.collection_id == collection_id).select().first()
    if row:
        row = db((db.collections.collection_id == collection_id) &
                 (db.collections.part == part)).select().first()

        if row and row.client_id == client_id:
            response.headers[blobstore.BLOB_KEY_HEADER] = row.blob_key
            response.headers["Content-Type"] = "application/json"
        else:
            raise http.HTTP(404, "collection not found")
