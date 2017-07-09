import time

from gluon import html

from rekall_lib.types import actions
from rekall_lib.types import agent
from api import users
from api import utils


def list(current):
    db = current.db
    result = []
    for row in db(db.hunts.id > 0).select():
        result.append(dict(
            hunt_id=row.hunt_id,
            labels=[x for x in row.labels if x],
            flow=row.flow.to_primitive(),
            timestamp=row.timestamp,
            creator=row.creator,
            state=row.state,
            status=row.status.to_primitive()));

    return dict(data=result)


def results(current, hunt_id):
    db = current.db
    result = []
    for row in db(db.hunt_status.hunt_id == hunt_id).select():
        # TODO: This might be a bit slow. Think about reworking the UI to be
        # more efficient here.
        collection_ids = [
            x.collection_id for x in
            db((db.collections.flow_id == hunt_id) &
               (db.collections.client_id == row.client_id)).select()]

        result.append(dict(
            client_id=row.client_id,
            collection_ids=collection_ids,
            status=row.status.to_primitive()))

    return dict(data=result)


def propose_from_flows(current, flow_ids, labels, approvers, name=None):
    """Launch a hunt from the flows on these labels."""
    hunt_id = utils.new_hunt_id()
    now = time.time()

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
        return "ok"
