"""Implements demo specific APIs."""
from rekall_lib.rekall_types import agent

from api import audit
from api import users
from api import utils


def make_me_admin(current):
    """Makes the current user into an admin."""
    users.add(current, utils.get_current_username(current), "/", "Administrator")
    users.add(current, utils.get_current_username(current), "/", "Viewer")

    return {}


TABLES = [
    "audit",
    "clients",
    "client_logs",
    "flows",
    "hunts",
    "hunt_status",
    "collections",
    "uploads",
    "upload_files",
    "artifacts",
    "canned_flows",
    "labels",
    "permissions",
    "notifications",
    "tokens"
]


def clear_all_data(current):
    """Clears all the data."""
    db = current.db
    try:
        for table in TABLES:
            db(getattr(db, table).id > 0).delete()
    finally:
        audit.log(current, "DemoClearedTable")


class DemoClearedTable(agent.AuditMessage):
    schema = [
        dict(name="format",
             default="%(user)s cleared all tables.")
    ]
