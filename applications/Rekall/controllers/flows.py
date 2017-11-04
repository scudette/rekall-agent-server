# Launch flows controller.  TODO: This file does not do much but relay the
# request to the view. Maybe we can just deprecate all controllers?
# Since we use the API now for everything there is no point of them.


def description():
    client_id = request.vars.client_id
    flow_id = request.vars.flow_id
    if client_id and flow_id:
        return dict(client_id=client_id,
                    flow_id=flow_id)

def list():
    client_id = request.vars.client_id
    if client_id:
        return dict(client_id=client_id)

    raise HTTP(400, "client_id must be provided.")


def inspect_list():
    client_id = request.vars.client_id
    return dict(client_id=client_id)


def hex_view():
    upload_id = request.vars.upload_id
    offset = request.vars.offset or 0
    client_id = request.vars.client_id
    flow_id = request.vars.flow_id
    return dict(upload_id=upload_id,
                offset=offset,
                client_id=client_id,
                flow_id=flow_id)


def list_canned():
    return dict()


def launch():
    plugin = request.vars.plugin
    client_id = request.vars.client_id
    return dict(plugin=plugin, client_id=client_id)


def collection_view():
    """Render the collection.

    Note the actual data is streamed from Blobstore. This controller just
    creates the viewing page.
    """
    part = request.vars.part or 0
    if request.vars.collection_id:
        return dict(collection_id=request.vars.collection_id,
                    client_id=request.vars.client_id,
                    flow_id=request.vars.flow_id,
                    part=part)

def save():
    flows = []
    flow_ids = request.vars.flows
    if flow_ids:
        for flow_id in flow_ids:
            row = db(db.flows.flow_id == flow_id).select().first()
            if row:
                flows.append(row.flow.to_primitive())

    return dict(flows=flows)
