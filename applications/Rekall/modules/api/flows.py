"""API implementations for interacting with flows."""
import json
from rekall_lib.types import agent


def list(current, client_id):
    """Inspect all the launched flows."""
    flows = []
    db = current.db
    if client_id:
        for row in db(db.flows.client_id == client_id).select(
            orderby=~db.flows.timestamp):
            status = agent.FlowStatus.from_json(row.status)
            flows.append(dict(
                flow=json.loads(row.flow),
                timestamp=row.timestamp,
                creator=row.creator,
                status=status.to_primitive(),
                collection_ids=status.collection_ids,
            ))

    return dict(data=flows)
