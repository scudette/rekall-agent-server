import time
import uuid

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
            labels=row.labels,
            flow=row.flow.to_primitive(),
            timestamp=row.timestamp,
            creator=row.creator,
            status=row.status.to_primitive()));

    return dict(data=result)


def launch_from_flows(current, flow_ids, labels):
    """Launch a hunt from the flows on these labels."""
    hunt_id = str(uuid.uuid4())
    now = time.time()

    result = agent.Flow.from_keywords(
        name="Hunt %s" % hunt_id,
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
                    collection_id = unicode(uuid.uuid4())
                    action = actions.PluginAction.from_keywords(
                        plugin=action.plugin,
                        rekall_session=action.rekall_session,
                        collection=dict(
                            __type__="JSONCollection",
                            id=collection_id,
                            location=dict(
                                __type__="BlobUploader",
                                base=html.URL(
                                    c="api", f="control", args=['upload'], host=True),
                                path_template=(
                                    "collection/%s/{part}" % collection_id),
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
        timestamp=now)

    return {}
