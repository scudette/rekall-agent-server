"""Get information about collections."""
import json


def metadata(current, collection_id):
    db = current.db
    if collection_id:
        collection_row = db(
            db.collections.collection_id == collection_id).select().first()
        if collection_row:
            flow_id = collection_row.flow_id
            flow_row = db(db.flows.flow_id == flow_id).select().first()
            if flow_row:
                return dict(flow=json.loads(flow_row.flow),
                            status=json.loads(flow_row.status))

    return {}
