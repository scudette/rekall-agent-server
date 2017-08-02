"""A general purpose auditing module."""

from rekall_lib import serializer
from rekall_lib.types import agent
from api import utils
import datetime


def log(current, type, **kwargs):
    kwargs["__type__"] = type
    user = kwargs["user"] = utils.get_current_username(current)

    # Access was made via a token.
    if current.request.token:
        kwargs["token_id"] = current.request.token.token_id

    current.db.audit.insert(timestamp=datetime.datetime.now(),
                            message=serializer.unserialize(kwargs),
                            user=user, type=type)



def search(current, query):
    db = current.db
    query = query.strip()
    if query == "":
        condition = current.db.audit.id > 0

    elif query.startswith("type:"):
        type = query.split(":", 1)[1]
        condition = (current.db.audit.type == type)
    else:
        # Bare query searches for username.
        condition = (current.db.audit.user == query)

    result = []
    for row in db(condition).select(
            orderby_on_limitby=False, limitby=(0, 10000)):
        result.append(dict(text=row.message.format_message(),
                           message=row.message.to_primitive(),
                           timestamp=row.timestamp))

    log(current, "AuditSearch", query=query)

    return dict(data=result)


class ClientSearch(agent.AuditMessage):
    schema = [
        dict(name="format",
             default="%(user)s searched for clients with query '%(query)s'"),
        dict(name="query",
             doc="The query string used for searching"),
    ]


class AuditSearch(agent.AuditMessage):
    schema = [
        dict(name="format",
             default="%(user)s searched audit log with query '%(query)s'"),
        dict(name="query",
             doc="The query string used for searching"),
    ]


class ApprovalRequest(agent.AuditMessage):
    schema = [
        dict(name="client_id"),
        dict(name="approver"),
        dict(name="role"),
        dict(name="format",
             default="%(user)s asked %(approver)s for "
             "%(role)s access to %(client_id)s")
    ]

class ApprovalGranted(agent.AuditMessage):
    schema = [
        dict(name="client_id"),
        dict(name="approvee"),
        dict(name="role"),
        dict(name="format",
             default="%(user)s granted %(approvee)s "
             "%(role)s access to %(client_id)s")
    ]


class CollectionDownload(agent.AuditMessage):
    schema = [
        dict(name="collection_id"),
        dict(name="format",
             default="%(user)s downloaded %(collection_id)s")
    ]

class FileDownload(agent.AuditMessage):
    schema = [
        dict(name="upload_id"),
        dict(name="filename"),
        dict(name="format",
             default="%(user)s downloaded file %(upload_id)s")
    ]


class FlowLaunchPlugin(agent.AuditMessage):
    schema = [
        dict(name="client_id"),
        dict(name="flow_id"),
        dict(name="plugin"),
        dict(name="format",
             default="%(user)s launched %(plugin)s on %(client_id)s"),
    ]

class FlowLaunchCanned(agent.AuditMessage):
    schema = [
        dict(name="client_id"),
        dict(name="flow_id"),
        dict(name="canned_flow"),
        dict(name="format",
             default="%(user)s launched Canned Flow %(canned_flow)s on %(client_id)s"),
    ]

class HuntProposal(agent.AuditMessage):
    schema = [
        dict(name="hunt_id"),
        dict(name="format",
             default="%(user)s proposed hunt %(hunt_id)s")
    ]

class HuntApproval(agent.AuditMessage):
    schema = [
        dict(name="hunt_id"),
        dict(name="format",
             default="%(user)s approved hunt %(hunt_id)s")
    ]
