"""API implementations for interacting with flows."""
import time
import uuid

from gluon import html
from rekall_lib.types import actions
from rekall_lib.types import agent

from api import firebase
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
        #file_upload=dict(
        #    __type__="FileUploadLocation",
        #    flow_id=flow_id,
        #    base=html.URL(c="control", f='file_upload', host=True)),
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
                 rekall_session=rekall_session,
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

    firebase.notify_client(client_id)


def make_canned_flow(current, flow_ids, client_id):
    """Merge the flow ids into a single canned flow."""
    result = agent.CannedFlow()
    db = current.db
    seen = set()
    for flow_id in flow_ids:
        row = db(db.flows.flow_id == flow_id).select().first()
        if row:
            for action in row.flow.actions:
                if isinstance(action, actions.PluginAction):
                    canned_action = actions.PluginAction.from_keywords(
                        plugin=action.plugin,
                        rekall_session=action.rekall_session,
                        args=action.args)

                    # Dedupe identical canned actions.
                    key = canned_action.to_json()
                    if key in seen:
                        continue

                    seen.add(key)
                    result.actions.append(canned_action)

    return result.to_primitive()


def save_canned_flow(current, canned_flow):
    canned = agent.CannedFlow.from_json(canned_flow)
    db = current.db
    if not canned.name or not canned.category:
        raise ValueError(
            "Canned flows must have a name, and category")

    # Check to see if there is a canned flow of the same name:
    row = db(db.canned_flows.name == canned.name).select().first()
    if row:
        raise ValueError("There is already a canned flow with name '%s'" %
                         canned.name)

    db.canned_flows.insert(
        name=canned.name,
        description=canned.description,
        category=canned.category,
        flow=canned)

    return canned.to_primitive()

def list_canned_flows(current):
    db = current.db
    result = []
    for row in db(db.canned_flows.id > 0).select():
        result.append(row.flow.to_primitive())

    return dict(data=result)

def delete_canned_flows(current, names):
    db = current.db
    for name in names:
        db(db.canned_flows.name == name).delete()

    return {}


def launch_canned_flows(current, client_id, name):
    db = current.db
    row = db(db.canned_flows.name == name).select().first()
    if not row:
        raise ValueError("There is no canned flow with name '%s'" % name)

    for action in row.flow.actions:
        collection_id = unicode(uuid.uuid4())
        action.collection = dict(
            __type__="JSONCollection",
            id=collection_id,
            location=dict(
                __type__="BlobUploader",
                base=html.URL(
                    c="api", f="control", args=['upload'], host=True),
                path_template=(
                    "collection/%s/{part}" % collection_id),
            ))

    flow_id = unicode(uuid.uuid4())
    flow = agent.Flow.from_keywords(
        name=name,
        flow_id=flow_id,
        created_time=time.time(),
        ticket=dict(
            location=dict(
                __type__="HTTPLocation",
                base=utils.route_api('/control/ticket'),
                path_prefix=flow_id,
            )),
        actions=row.flow.actions,
    )

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

    firebase.notify_client(client_id)

    return {}
