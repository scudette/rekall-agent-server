

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
