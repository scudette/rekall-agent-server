

def view():
    return dict()


def list():
    return dict(hunt_id=request.vars.hunt_id)

def approve_request():
    """Approves a request from another user."""
    hunt_id = request.vars.hunt_id
    user = request.vars.user
    if hunt_id and user:
        return dict(hunt_id=hunt_id, user=user)


def hunts_clients():
    hunt_id = request.vars.hunt_id
    if hunt_id:
        return dict(hunt_id=hunt_id)


def describe_client():
    client_id = request.vars.client_id
    hunt_id = request.vars.hunt_id
    if client_id and hunt_id:
        return dict(client_id=client_id,
                    hunt_id=hunt_id)
