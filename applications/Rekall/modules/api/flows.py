"""API implementations for interacting with flows."""
import time
import uuid

from gluon import html
from rekall_lib.types import agent

from api import users
from api import utils


def list(current, client_id):
    """Inspect all the launched flows."""
    flows = []
    db = current.db
    if client_id:
        for row in db(db.flows.client_id == client_id).select(
            orderby=~db.flows.timestamp):
            flows.append(dict(
                flow=row.flow.to_primitive(),
                timestamp=row.timestamp,
                creator=row.creator,
                status=row.status.to_primitive(),
                collection_ids=row.status.collection_ids,
            ))

    return dict(data=flows)


def launch_plugin_flow(current, client_id, rekall_session, plugin, plugin_arg):
    """Launch the flow on the client."""
    db = current.db
    collection_id = unicode(uuid.uuid4())
    flow_id = unicode(uuid.uuid4())
    flow = agent.Flow.from_keywords(
        flow_id=flow_id,
        created_time=time.time(),
        rekall_session=rekall_session,
        file_upload=dict(
            __type__="FileUploadLocation",
            flow_id=flow_id,
            base=html.URL(c="control", f='file_upload', host=True)),
        ticket=dict(
            location=dict(
                __type__="HTTPLocation",
                base=utils.route_api('/control/ticket'),
                path_prefix=flow_id,
            )),
        actions=[
            dict(__type__="PluginAction",
                 plugin=plugin,
                 args=plugin_arg,
                 collection=dict(
                     __type__="JSONCollection",
                     id=collection_id,
                     location=dict(
                         __type__="BlobUploader",
                         base=html.URL(
                             c="api", f="control", args=['upload'], host=True),
                         path_template=(
                             "collection/%s/{part}" % collection_id),
                     ))
            )])

    db.flows.insert(
        flow_id=flow_id,
        client_id=client_id,
        status=agent.FlowStatus.from_keywords(
            timestamp=time.time(),
            client_id=client_id,
            flow_id=flow_id,
            status="Pending"),
        creator=users.get_current_username(),
        flow=flow,
    )

    db.collections.insert(
        collection_id=collection_id,
        flow_id=flow_id)
