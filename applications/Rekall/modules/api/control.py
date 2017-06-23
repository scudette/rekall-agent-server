"""This part of the API is communicated directly with the client."""
import datetime
import time

from rekall_lib.types import agent
from rekall_lib.types import client
from rekall_lib.types import location

from google.appengine.ext import blobstore
from google.appengine.api import app_identity

from api import utils


def manifest(_):
    """Serve the installation manifest to the client."""
    result = agent.Manifest.from_keywords(
        startup=dict(
            # Drop progress reports when running this flow.
            ticket=dict(location=location.DevNull()),
            actions=[
                client.StartupAction.from_keywords(
                    rekall_session=dict(live="API"),
                    location=dict(
                        __type__="HTTPLocation",
                        base=utils.route_api("control/startup"),
                    )
                )
            ]))

    return result.to_primitive()


def startup(current):
    """Called by the client when it starts up to provide a status update."""
    client_message = client.StartupMessage.from_json(
        current.request.body.getvalue())

    # Record the client event.
    current.db.client_logs.insert(client_id=current.client_id,
                          event='Startup',
                          data_type="StartupMessage",
                          data=client_message.to_primitive())

    for label in client_message.labels:
        current.db.labels.update_or_insert(
            current.db.labels.name == label,
            name=label)

    current.db.clients.update_or_insert(
        current.db.clients.client_id == current.client_id,
        client_id=current.client_id,
        hostname=client_message.system_info.node,
        labels=client_message.labels,
        summary=client_message.to_primitive())

    return {}


def jobs(current, last_flow_time=0):
    """List all the jobs intended for this client."""
    db = current.db
    result = agent.JobFile()
    last_flow_time = int(last_flow_time)
    for row in db((db.flows.client_id == current.client_id) &
                  (db.flows.timestamp > last_flow_time)).select():
        # Send off newly scheduled flows.
        if row.status.status == 'Pending':
            row.status.status = "Started"
            row.update_record(status=row.status)
            result.flows.append(row.flow)

    # Update metadata about the client.
    row = db(db.clients.client_id == current.client_id).select().first()
    if row:
        request = current.request
        last_info = agent.LastClientState.from_keywords(
            timestamp=time.time(),
            latlong=request.env["HTTP_X-AppEngine-CityLatLong"],
            city=request.env["HTTP_X-AppEngine-City"],
            ip=request.client)
        row.update_record(last=datetime.datetime.utcnow(),
                          last_info=last_info)

        # Now check for hunts for this client.
        labels = set(utils.BaseValueList(row.labels)).union(
            utils.BaseValueList(row.custom_labels))
        for hunts in db(
            db.hunts.labels.belongs(labels) &
            (db.hunts.timestamp > last_flow_time)).select():
            result.flows.append(hunts.flow)

    return result.to_primitive()


def ticket(current, flow_id):
    """Client use this to report the progress of a flow."""
    db = current.db
    row = db(db.flows.flow_id == flow_id).select().first()
    if row:
        # Update the status from the client.
        status = agent.FlowStatus.from_json(current.request.body.getvalue())
        row.update_record(status=status)

    return dict()



# Interact with FileUploadLocationImpl

def file_upload(current, upload_request):
    """Request an upload ticket for commencing file upload."""
    upload_request = location.FileUploadRequest.from_json(
        upload_request)

    return location.FileUploadResponse.from_keywords(
        url=blobstore.create_upload_url(
            utils.route_api("/control/file_upload_receive",
                            upload_request=upload_request.to_json()),
            gs_bucket_name=app_identity.get_default_gcs_bucket_name())
    ).to_primitive()


def file_upload_receive(current, upload_request):
    upload_request = location.FileUploadRequest.from_json(
        upload_request)
    db = current.db
    file_info = blobstore.parse_file_info(current.request.vars['file'])
    gs_object_name = file_info.gs_object_name
    blob_key = blobstore.create_gs_key(gs_object_name)

    upload_id = db.uploads.insert(
        blob_key=blob_key,
        state="received")

    db.upload_files.insert(
        file_information=upload_request.file_information.to_primitive(),
        upload_id=upload_id,
        flow_id=upload_request.flow_id)

    return dict()


def upload(current, type, collection_id, part=0):
    result = location.BlobUploadSpecs.from_keywords(
        url=blobstore.create_upload_url(
            utils.route_api("/control/upload_receive",
                            type=type,
                            collection_id=collection_id,
                            part=part, client_id=current.client_id),
            gs_bucket_name=app_identity.get_default_gcs_bucket_name())
    ).to_primitive()
    return result


def upload_receive(current, type, collection_id, part=0, client_id=None):
    """Handle GCS callback.

    The user uploads to GCS directly and once the upload is complete, GCS calls
    this handler with the file information. This API is not normally called
    directly.
    """
    db = current.db
    file_info = blobstore.parse_file_info(current.request.vars['file'])
    gs_object_name = file_info.gs_object_name
    blob_key = blobstore.create_gs_key(gs_object_name)

    db.collections.update_or_insert(
        db.collections.collection_id == collection_id,
        client_id=client_id,
        collection_id=collection_id,
        part=part,
        blob_key=blob_key,
        gs_object_name=gs_object_name)

    return dict()
