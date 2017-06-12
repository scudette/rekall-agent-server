import functools
import json
import os
import yaml

import gluon
from api import types
from google.appengine.api import users
from google.appengine.ext import ndb


toplevel = os.path.dirname(__file__) + "/../.."

_roles = yaml.load(open(
    os.path.join(toplevel, "private", "roles.yaml")).read())

_roles_to_permissions = dict((x["role"], x["permissions"]) for x in _roles)
_roles_by_name = dict((x["role"], x) for x in _roles)

# All known roles
roles = set(_roles_to_permissions)

_permissions_to_roles = {}
for role_, permissions in _roles_to_permissions.iteritems():
    for permission in permissions:
        _permissions_to_roles.setdefault(permission, []).append(role_)


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

        print "Is admin: %s" % users.is_current_user_admin()
        if users.is_current_user_admin():
            return True

    query = ((db.permissions.resource == resource) &
             (db.permissions.user == user) &
             (db.permissions.role.belongs(
                 permission_to_roles(permission))))

    result = False
    for row in db(query).select():
        return True
    return False


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
