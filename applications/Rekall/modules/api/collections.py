"""Get information about collections."""
from __future__ import absolute_import
import collections

from google.appengine.ext import blobstore
from api import audit
from api import users


def metadata(current, collection_id, client_id):
    db = current.db
    flow_row = None

    if collection_id:
        collection_row = db(
            db.collections.collection_id == collection_id).select().first()
        if collection_row:
            flow_id = collection_row.flow_id
            # Flow.
            if flow_id.startswith("F"):
                flow_row = db(db.flows.flow_id == flow_id).select().first()
            # Hunt.
            elif flow_id.startswith("H"):
                flow_row = db(db.hunts.hunt_id == flow_id).select().first()

            if flow_row:
                return dict(flow=flow_row.flow.to_primitive(),
                            status=flow_row.status.to_primitive())

    return {}

metadata.args = collections.OrderedDict(
    collection_id="The collection id to examine.",
    client_id="The client owning the collection (used for ACL checks).")


def get(current, collection_id, part=0):
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

        if row:
            response.headers[blobstore.BLOB_KEY_HEADER] = row.blob_key
            response.headers["Content-Type"] = "application/json"

            audit.log(current, "CollectionDownload", collection_id=collection_id)

        else:
            raise ValueError("collection not found")

get.args = collections.OrderedDict(
    collection_id="The collection id to examine.",
    client_id="The client owning the collection (used for ACL checks).",
    part="The part of the collection (used for large collections)")



def require_collection_access(current):
    """Determine if the user has access to the collection."""
    collection_id = current.request.vars.collection_id
    db = current.db
    if collection_id:
        row = db(db.collections.collection_id == collection_id).select().first()
        if row:
            if row.client_id:
                client_resource = "/" + row.client_id
                if users.check_permission(current, "clients.view",
                                          client_resource):
                    return True

            if row.flow_id:
                flow_resource = "/" + row.flow_id
                if users.check_permission(current, "flows.view",
                                          flow_resource):
                    return True

                if users.check_permission(current, "hunts.view",
                                          flow_resource):
                    return True

    raise users.PermissionDenied("clients.view", collection_id)
