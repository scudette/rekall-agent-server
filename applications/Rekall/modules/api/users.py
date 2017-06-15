import functools
import os
import urlparse
import yaml

import gluon
from api import types
from gluon import http
from google.appengine.api import users

from rekall_lib import crypto
from rekall_lib import serializer


toplevel = os.path.dirname(__file__) + "/../.."

_roles = yaml.load(open(
    os.path.join(toplevel, "private", "roles.yaml")).read())

_roles_to_permissions = dict((x["role"], x["permissions"]) for x in _roles)
_roles_by_name = dict((x["role"], x) for x in _roles)

# All known roles
roles = set(_roles_to_permissions)

_permissions_to_roles = {}
for role_, permissions in _roles_to_permissions.iteritems():
    for _ in permissions:
        _permissions_to_roles.setdefault(_, []).append(role_)


# All known permissions
permissions = set(_permissions_to_roles)


def role_to_permissions(role):
    return _roles_to_permissions.get(role, [])


def permission_to_roles(permission):
    return _permissions_to_roles.get(permission, [])


def check_permission(current, permission, resource, user=None):
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
    db = current.db
    if user is None:
        user = users.get_current_user()
        if not user:
            return False
        user = user.email()

        if users.is_current_user_admin():
            return True

    query = ((db.permissions.resource == resource) &
             (db.permissions.user == user) &
             (db.permissions.role.belongs(
                 permission_to_roles(permission))))

    result = False
    # TODO: Implement conditions.
    for row in db(query).select():
        return True
    return False


def is_user_app_admin():
    return users.is_current_user_admin()


def require(current, permission, resource=lambda req: "/"):
    """A decorator on a controller which requires a permission.

    Raises 403 Unauthorized if the permission is missing.
    """
    def decorator(func):

        @functools.wraps(func)
        def wrapper(*args, **kword):
            # If the user is not logged in, redirect them to the log in page.
            user = users.get_current_user()
            if not user:
                gluon.redirect(users.create_login_url(current.request.url))

            resource_name = resource
            if callable(resource):
                resource_name = resource(current.request)

            if check_permission(current, permission, resource_name):
                return func(*args, **kword)

            gluon.redirect(gluon.URL("logout"))

        return wrapper
    return decorator


def list(current):
    """List all the users."""
    db = current.db
    return dict(data=db(db.permissions).select().as_list())


def add(current, user, resource, role, condition=None):
    """Add a new user role grant."""
    db = current.db
    db.permissions.update_or_insert(
        dict(user=user, resource=resource, role=role),
        user=user,
        resource=resource,
        role=role,
        condition=types.IAMCondition.from_json(condition or "{}"))


def delete(current):
    """Remove a user binding."""
    db = current.db
    request = current.request
    user = request.vars.user
    resource = request.vars.resource or "/"
    role = request.vars.role

    db((db.permissions.user == user) &
       (db.permissions.resource == resource) &
       (db.permissions.role == role)).delete()


def get_role(current, role):
    """Get a role description"""
    return _roles_by_name.get(role, {})


def get_current_username():
    user = users.get_current_user()
    if not user:
        return ""
    return user.email()


def redirect_error(permission, resource):
    raise http.HTTP(403, """
You do not have a required permission: %s on resource %s.
Please contact your administrator to be granted the required
permission.""" % (permission, resource))


# The following decorators are used to ensure that the current request complies
# with the required permission.

def anonymous_access(request):
    """Anyone can access this API."""
    pass


def require_client(permission):
    """Requires client level permission."""
    def wrapper(current):
        resource = "/"
        client_id = current.request.vars.client_id
        if client_id:
            resource = "/" + client_id
            if check_permission(current, permission, resource):
                return True

        redirect_error(permission, resource)

    return wrapper


def require_application(permission):
    """Requires application level permission."""
    def wrapper(current):
        resource = "/"
        if check_permission(current, permission, resource):
            return True

        redirect_error(permission, resource)

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
        # Signatures are sent in this special header.
        header = current.request.env['HTTP_X_REKALL_SIGNATURE']
        if not header:
            raise http.HTTP(403)

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

        raise http.HTTP(403)

    return wrapper


def require_admin():
    """Requires admin level access (for user management)."""
    def wrapper(current):
        resource = "/"
        permission = "users.admin"
        if check_permission(current, permission, resource):
            return True

        redirect_error(permission, resource)

    return wrapper


def count_notifications(current):
    user = get_current_username()
    db = current.db
    return db((db.notifications.user == user) &
              (db.notifications.read == False)).count()


def send_notifications(current, user, message_id, args):
    """Send a notification to the user."""
    db = current.db
    db.notifications.insert(
        from_user=get_current_username(),
        user=user,
        message_id=message_id,
        args=args)

    return "ok"


def read_notifications(current):
    db = current.db
    result = []

    for row in db(db.notifications.user == get_current_username()).select():
        result.append(row.as_dict())
        if not row.read:
            row.update_record(read=True)

    return dict(data=result)


def clear_notifications(current):
    db = current.db

    db((db.notifications.user == get_current_username()) &
       (db.notifications.read == True)).delete()

    return dict()
