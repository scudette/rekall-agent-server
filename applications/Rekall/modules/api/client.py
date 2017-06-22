"""Methods for accessing clients."""
from __future__ import absolute_import

import collections
import json

from api import users


def search(current, query=None):
    if not query:
        raise ValueError("query must be provided.")

    query = query.strip()
    condition = current.db.clients.id > 0

    # Search for a client ID directly.
    if query.startswith("C."):
        condition = current.db.clients.client_id == query
    else:
        # AppEngine uses Bigtable which does not support `like` operation. We
        # only support a prefix match.
        condition = ((current.db.clients.hostname >= query) &
                     (current.db.clients.hostname < query + u"\ufffd"))

    result = []
    for row in current.db(condition).select():
        result.append(dict(
            last=row.last,
            client_id=row.client_id,
            summary=json.loads(row.summary)))

    return dict(data=result)

search.args = collections.OrderedDict(
    query="The query string. If it starts with a 'C.' then we display an exact "
    "match. Otherwise we search for a hostname prefix.")


def list_approvers(current, client_id):
    """List users which can approve client access."""
    db = current.db
    # TODO: implement conditions.
    approvers = []
    for row in db(db.permissions.role == "Approver").select():
        approvers.append(row.user)

    return dict(data=approvers)


def request_approval(current, client_id, approver, role):
    """Request an approval from the specified user."""

    # Notify the approver that a request is pending.
    users.send_notifications(
        current, approver, "APPROVAL_REQUEST", dict(
            client_id=client_id,
            user=users.get_current_username(current),
            role=role))

request_approval.args = collections.OrderedDict(
    client_id="The client to grant access to.",
    approver="The user that should approve the request.",
    role="The role granted.")


def approve_request(current, client_id, user, role):
    """Grant the approval for the client."""
    # Validate the client_id.
    if (client_id.startswith("C.") and len(client_id.split("/")) == 1 and
        role in ["Examiner", "Investigator"]):
        users.add(current, user, "/" + client_id, role)

        return "ok"

approve_request.args = collections.OrderedDict(
    client_id="The client to grant access to.",
    user="The user getting the approval.",
    role="The role granted.")
