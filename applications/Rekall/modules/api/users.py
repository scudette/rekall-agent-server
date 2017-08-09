import datetime
import logging
import os
import urlparse
import yaml

from api import audit
from api import types
from api import utils

from gluon import http
from google.appengine.api import users

from rekall_lib import crypto
from rekall_lib import serializer
from rekall_lib.types import agent


toplevel = os.path.dirname(__file__) + "/../.."

_roles = yaml.load(open(
    os.path.join(toplevel, "private", "roles.yaml")).read())

_roles_to_permissions = dict((x["role"], set(x["permissions"])) for x in _roles)
_roles_by_name = dict((x["role"], x) for x in _roles)

# All known roles
roles = set(_roles_to_permissions)

_permissions_to_roles = {}
for role_, permissions in _roles_to_permissions.iteritems():
    for _ in permissions:
        _permissions_to_roles.setdefault(_, []).append(role_)


# All known permissions
permissions = set(_permissions_to_roles)


class PermissionDenied(http.HTTP):
    """Raised for unauthorized errors."""
    def __init__(self, permission="", resource=""):
        super(PermissionDenied, self).__init__(403)
        self.permission = permission
        self.resource = resource


def role_to_permissions(role):
    return _roles_to_permissions.get(role, [])


def permission_to_roles(permission):
    return _permissions_to_roles.get(permission, [])


def check_permission(current, permission, resource, user=None,
                     with_tokens=True):
    """Check if user has permission on resource.

    This is the low level primitive for checking access.

    NOTE: Admin users always get access regardless of role. An admin user is one
    which has the Viewer/Editor/Admin role on the AppEngine application using
    GCP IAM mechanism (see
    https://cloud.google.com/appengine/docs/standard/python/users/adminusers).

    Note: This allows the application to be initially installed as the user
    which deploys it will be granted AppEngine Admin by the platform, and this
    allows them to add other users to application roles.
    """
    # Check with token. Note that token access is not CSRF protected because
    # token access is used for non-browser, scripted access (e.g. using curl or
    # wget).
    token = current.request.vars.token
    if with_tokens and token:
        token_info = check_permission_with_token(
            current, permission, resource, token)
        if token_info:
            current.request.token = token_info
            return True

        # User presented a token but it was invalid.
        return False

    db = current.db
    if user is None:
        user = users.get_current_user()
        if not user:
            return False
        user = user.email()

        if is_user_app_admin():
            return True

    query = ((db.permissions.resource == resource) &
             (db.permissions.user == user) &
             (db.permissions.role.belongs(
                 permission_to_roles(permission))))

    # TODO: Implement conditions.
    for row in db(query).select():
        logging.debug("Permission granted for %s with %s on %s",
                      user, permission, resource)
        return True

    logging.debug("Permission denied for %s with %s on %s",
                  user, permission, resource)
    return False


def check_permission_with_token(current, permission, resource, token):
    db = current.db
    row = db(db.tokens.token_id == token).select().first()
    if row:
        # Is the token expired?
        if datetime.datetime.utcnow() > row.expires:
            return False

        # First check that delegator has permission to delegate in the first
        # place.
        if not check_permission(current, permission, resource,
                                user=row.delegator, with_tokens=False):
            return False

        # All roles are delegated.
        if row.role == "All":
            return row.as_dict()

        # Check that permission is granted by the delegated role.
        if permission in _roles_to_permissions.get(row.role, []):
            return row.as_dict()

    return False


def is_user_app_admin():
    logging.debug("is_user_app_admin: %s", users.is_current_user_admin())
    return users.is_current_user_admin()


def list(current):
    """List all the users."""
    db = current.db
    return dict(data=db(db.permissions).select().as_list())


def add(current, user, resource, role, condition="{}"):
    """Add a new user role grant."""
    db = current.db
    if role not in roles:
        raise ValueError("Role %s is not valid." % role)

    db.permissions.update_or_insert(
        dict(user=user, resource=resource, role=role),
        user=user,
        resource=resource,
        role=role,
        condition=types.IAMCondition.from_json(condition))

    audit.log(current, "UserAdd", username=user, resource=resource, role=role)

    return {}

def delete(current, user, role, resource="/"):
    """Remove a user binding."""
    db = current.db

    db((db.permissions.user == user) &
       (db.permissions.resource == resource) &
       (db.permissions.role == role)).delete()

    audit.log(current, "UserDelete", username=user, resource=resource, role=role)

    return {}


def get_role(current, role):
    """Get a role description"""
    return _roles_by_name.get(role, {})


def list_roles(current):
    return dict(roles=[x for x in roles])


def my(current):
    """List all of the calling user's roles."""
    db = current.db
    result = []
    for row in db(
        db.permissions.user == utils.get_current_username(current)).select():
        result.append(row.as_dict())

    return dict(data=result)


# The following decorators are used to ensure that the current request complies
# with the required permission.

def anonymous_access():
    """Anyone can access this API."""
    def wrapper(current):
        pass

    return wrapper


def require_client(permission):
    """Requires client level permission."""
    def wrapper(current):
        resource = "/"
        client_id = current.request.vars.client_id
        if client_id:
            resource = "/" + client_id
            if check_permission(current, permission, resource):
                return True

        raise PermissionDenied(permission, resource)

    return wrapper


def require_flow(permission):
    """Requires flow or hunt level permission."""
    def wrapper(current):
        resource = "/"
        flow_id = (current.request.vars.flow_id or
                   current.request.vars.hunt_id)
        if flow_id:
            resource = "/" + flow_id
            if check_permission(current, permission, resource):
                return True

        raise PermissionDenied(permission, resource)

    return wrapper


def require_application(permission):
    """Requires application level permission."""
    def wrapper(current):
        resource = "/"
        if check_permission(current, permission, resource):
            return True

        raise PermissionDenied(permission, resource)

    return wrapper


def require_client_authentication():
    """Require authentication from the client.

    This checks that requests are sent from valid clients which belong to this
    deployment. Clients authenticate their messages by including a signature in
    the x-rekall-signature header.

    NOTE: We assume all client communication occurs over HTTPS. Therefore:
    - Data can not be interfered while in transit.
    - Data can not be replayed.
    - Clients know and trust server.

    The main threat model is a client impersonating another client.

    - This is addressed by using a client id derived from the public key of the
      client.

    - The client keeps it's private key secret and uses it to sign every
      transaction.

    - The server verifies the transaction and extracts the client's id from the
      public key the client advertises.

    Clients can not impersonate other clients. If the client changes its key, it
    will necessarily change its ID as well. It should be impossible to create a
    new key which hashes to the same client id as another client.
    """
    def wrapper(current):
        header = current.request.env['HTTP_X_REKALL_SIGNATURE']
        if not header:
            raise PermissionDenied()

        header = serializer.unserialize(header, strict_parsing=False,
                                        type=crypto.HTTPSignature)
        if header:
            if header.public_key:
                current.client_id = header.public_key.client_id()
                data = ""
                data = current.request.body.getvalue()
                if header.public_key.verify(header.assertion + data,
                                            header.signature):
                    assertion = serializer.unserialize(header.assertion,
                                                       strict_parsing=False)
                    if assertion:
                        asserted_url = urlparse.urlparse(assertion.url)
                        our_url = urlparse.urlparse(
                            current.request.env.web2py_original_uri or "")
                        if asserted_url.path == our_url.path:
                            return True

        raise PermissionDenied()

    return wrapper


def require_admin():
    """Requires admin level access (for user management)."""
    def wrapper(current):
        resource = "/"
        permission = "users.admin"
        if check_permission(current, permission, resource):
            return True

        raise PermissionDenied(permission, resource)

    return wrapper


def count_notifications(current):
    user = utils.get_current_username(current)
    db = current.db
    return db((db.notifications.user == user) &
              (db.notifications.read == False)).count()


def send_notifications(current, user, message_id, args):
    """Send a notification to the user."""
    db = current.db
    db.notifications.insert(
        from_user=utils.get_current_username(current),
        user=user,
        message_id=message_id,
        args=args)

    return {}


def read_notifications(current):
    db = current.db
    result = []

    for row in db(
        db.notifications.user == utils.get_current_username(current)).select():
        result.append(row.as_dict())
        if not row.read:
            row.update_record(read=True)

    return dict(data=result)


def clear_notifications(current):
    db = current.db

    db((db.notifications.user == utils.get_current_username(current)) &
       (db.notifications.read == True)).delete()

    return dict()


def mint_token(current, role, resource):
    # We can not mint tokens from delegated access!
    if current.request.token:
        raise PermissionDenied("token.mint", "/")

    db = current.db
    token_id = utils.new_token_id()
    db.tokens.insert(delegator=utils.get_current_username(current),
                     token_id=token_id,
                     role=role,
                     resource=resource)

    return dict(token=token_id)


class UserAdd(agent.AuditMessage):
    schema = [
        dict(name="username"),
        dict(name="resource"),
        dict(name="role"),
        dict(name="format",
             default="%(user)s added %(username)s as %(role)s on %(resource)s")
    ]

class UserDelete(agent.AuditMessage):
    schema = [
        dict(name="username"),
        dict(name="resource"),
        dict(name="role"),
        dict(name="format",
             default="%(user)s removed %(username)s as %(role)s on %(resource)s")
    ]
