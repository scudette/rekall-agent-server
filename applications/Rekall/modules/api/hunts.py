import time

from gluon import html

from rekall_lib.types import actions
from rekall_lib.types import agent
from api import users
from api import utils


def list(current):
    """List recent hunts."""
    db = current.db
    result = []
    for row in db(db.hunts.id > 0).select(
            orderby=~db.hunts.timestamp
    ):
        result.append(dict(
            hunt_id=row.hunt_id,
            labels=[x for x in row.labels if x],
            flow=row.flow.to_primitive(),
            timestamp=row.timestamp,
            creator=row.creator,
            state=row.state,
            status=row.status.to_primitive()))

    return dict(data=result)


def list_clients(current, hunt_id):
    db = current.db
    result = []
    for row in db(db.hunt_status.hunt_id == hunt_id).select():
        result.append(dict(client_id=row.client_id,
                           status=row.status.to_primitive()))

    return dict(data=result)


def describe_client(current, hunt_id, client_id):
    db = current.db
    row = db(db.hunts.hunt_id == hunt_id).select().first()
    if row:
        collection_ids = [
            x.collection_id for x in
            db((db.collections.flow_id == hunt_id) &
               (db.collections.client_id == client_id)).select()]

        file_infos = []
        for x in db((db.upload_files.flow_id == hunt_id) &
                    (db.upload_files.client_id == client_id)).select():
            file_infos.append(dict(
                upload_id=x.upload_id,
                file_information=x.file_information.to_primitive()))

        return dict(
            flow=row.flow.to_primitive(),
            creator=row.creator,
            timestamp=row.timestamp,
            status=row.status.to_primitive(),
            collection_ids=collection_ids,
            file_infos=file_infos)

    raise IOError("Hunt %s not found" % hunt_id)


def propose_from_flows(current, flow_ids, labels, approvers, name=None):
    """Launch a hunt from the flows on these labels."""
    hunt_id = utils.new_hunt_id()
    now = time.time()
    also_upload_files = False

    result = agent.Flow.from_keywords(
        name=name or hunt_id,
        flow_id=hunt_id,
        created_time=now,
        creator=users.get_current_username(current),
        ticket=dict(
            location=dict(
                __type__="HTTPLocation",
                base=utils.route_api('/control/hunt_ticket'),
                path_prefix=hunt_id,
            )),
    )

    db = current.db
    seen = set()
    for flow_id in flow_ids:
        row = db(db.flows.flow_id == flow_id).select().first()
        if row:
            for action in row.flow.actions:
                if action.rekall_session.get("also_upload_files"):
                    also_upload_files = True

                if isinstance(action, actions.PluginAction):
                    action = actions.PluginAction.from_keywords(
                        plugin=action.plugin,
                        rekall_session=action.rekall_session,
                        collection=dict(
                            __type__="JSONCollection",
                            location=dict(
                                __type__="BlobUploader",
                                base=html.URL(
                                    c="api", f="control", args=['upload'], host=True),
                                path_template=(
                                    "collection/%s/{part}" % hunt_id),
                            )),
                        args=action.args)

                    # Dedupe identical canned actions.
                    key = action.to_json()
                    if key in seen:
                        continue

                    seen.add(key)
                    result.actions.append(action)

    if also_upload_files:
        result.file_upload = dict(
            __type__="FileUploadLocation",
            flow_id=hunt_id,
            base=html.URL(c="api", f='control/file_upload',
                          host=True))

    # Add the hunt to the hunts table.
    db.hunts.insert(
        hunt_id=hunt_id,
        creator=result.creator,
        flow=result,
        labels=labels,
        state="Proposed",
        timestamp=now)

    for approver in approvers:
        users.send_notifications(
            current, approver, "HUNT_APPROVAL_REQUEST", dict(
                hunt_id=hunt_id,
                user=users.get_current_username(current)))

    return {}

def grant_approval(current, hunt_id, user):
    db = current.db
    row = db(db.hunts.hunt_id == hunt_id).select().first()
    if row and row.state == "Proposed":
        row.update_record(state="Started", timestamp=time.time())

        # Give the user permission over this hunt.
        users.add(current, user, "/" + hunt_id, "Examiner")
        return dict(data="ok")

    return {}


def requires_hunt_access(current):
    hunt_resource = ""
    hunt_id = current.request.vars.hunt_id
    db = current.db
    if hunt_id:
        row = db(db.hunts.hunt_id == hunt_id).select().first()
        if row:
            hunt_resource = "/" + row.hunt_id
            if users.check_permission(current, "hunts.view", hunt_resource):
                return True

    raise users.PermissionDenied("hunts.view", hunt_resource)
