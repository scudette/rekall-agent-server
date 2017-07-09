# Controller to manage clients.
import api
from api import utils

from gluon.globals import current


def search():
    return dict(q=request.vars.q)


def request_approval():
    """Request an approval to view client."""
    client_id = request.vars.client_id
    if client_id:
        roles = ["Examiner", "Investigator"]
        approvers = api.api_dispatcher.call(
            current, "client.approver.list", client_id).get("data")
        inputs = [SELECT(*roles,
                         _name="role",
                         requires=IS_IN_SET(roles)),
                  SELECT(*sorted(approvers),
                         _name="approver",
                         requires=IS_IN_SET(approvers)),
                  INPUT(_name="client_id", _value=client_id,
                        _type="hidden"),
        ]

        form = utils.build_form(inputs)
        return dict(form=form, client_id=client_id)


def approve_request():
    """Approves a request from another user."""
    client_id = request.vars.client_id
    role = request.vars.role
    user = request.vars.user
    if client_id and role and user:
        return dict(client_id=client_id, user=user, role=role)
