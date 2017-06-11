from google.appengine.ext import blobstore
from google.appengine.api import app_identity

from rekall_lib.types import location


# Interact with FileUploadLocationImpl

def file_upload():
    response.view = "generic.json"
    upload_request = location.FileUploadRequest.from_json(
        request.body.getvalue())

    return location.FileUploadResponse.from_keywords(
        url=blobstore.create_upload_url(
            URL(f='file_upload_receive',
                vars=dict(upload_request=upload_request.to_json()),
                host=True),
            gs_bucket_name=app_identity.get_default_gcs_bucket_name())
    ).to_primitive()


def file_upload_receive():
    response.view = "generic.json"
    upload_request = location.FileUploadRequest.from_json(
        request.vars.upload_request)

    file_info = blobstore.parse_file_info(request.vars['file'])
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


def upload():
    response.view = "generic.json"
    return location.BlobUploadSpecs.from_keywords(
        url=blobstore.create_upload_url(
            URL(f='upload_receive', args=request.args, host=True),
            gs_bucket_name=app_identity.get_default_gcs_bucket_name())
    ).to_primitive()


def upload_receive():
    """Handle GCS callback.

    The user uploads to GCS directly and once the upload is complete, GCS calls
    this handler with the file information.
    """
    try:
        type = request.args[0]
        if type == "collection":
            collection_id = request.args[1]
            part = int(request.args[2])

        else:
            raise HTTP(400, "upload type not supported")
    except (ValueError, IndexError) as e:
        raise HTTP(400, "id must be provided.")

    file_info = blobstore.parse_file_info(request.vars['file'])
    gs_object_name = file_info.gs_object_name
    blob_key = blobstore.create_gs_key(gs_object_name)

    db.collections.update_or_insert(
        db.collections.collection_id == collection_id,
        collection_id=collection_id,
        part=part,
        blob_key=blob_key,
        gs_object_name=gs_object_name)

    return dict()
