"""An API controller for exposing controllers as API.

This is similar to the web2py Service() object.
"""
# This loads API plugins from Rekall/modules/api/...
from gluon import http
import logging

from api import client
from api import collections
from api import control
from api import flows
from api import forensic_artifacts
from api import plugins
from api import uploads
from api import users



class MethodDesc(object):
    """A descriptor for an API method."""

    def __init__(self, method, args, doc="", args_desc=None, api_method=None):
        self.method = method
        self.api_method = api_method
        self.args = args
        self.doc = doc
        if args_desc is None:
            args_desc = dict((x, "") for x in args)

        self.args_desc = args_desc

    def convert_to_arrays(self, kwargs):
        """Web2py does not properly convert jquery's array notation."""
        for k in list(kwargs):
            if k.endswith("[]"):
                v = kwargs.pop(k)
                if isinstance(v, basestring):
                    v = [v]
                kwargs[k[:-2]] = v
        return kwargs

    def run(self, current, args, kwargs):
        return self.method(current, args, self.convert_to_arrays(kwargs))


class APIDispatcher(object):
    def __init__(self):
        self.dispatch = {}
        self.methods = []

    def error(self):
        raise http.HTTP(404, "Not Found")

    def register(self, path, method, security_managers=(lambda x: True,)):
        components = [x for x in path.split("/") if x]
        prefix_components = components[:-1]
        method_name = components[-1]
        container = self.dispatch
        for prefix_component in prefix_components:
            if prefix_component:
                container = container.setdefault(prefix_component, {})

        # The list of the method's args.
        method_args = method.func_code.co_varnames[
            :method.func_code.co_argcount]

        if method_args[0] not in ["current", "_"]:
            raise AttributeError(
                "API method %s must accept current as first parameter.",
                method.__name__)

        # First arg is always "current"
        method_args = method_args[1:]

        def run_method_cb(current, pos_args, kwargs):
            """A controller function which will launched to handle the API."""
            # Ensure the security manager allows this:
            for security_manager in security_managers:
                security_manager(current)

            # We allow method args to be called as positional or keyword
            local_kwargs = {}
            for i, arg_name in enumerate(method_args):
                if i < len(pos_args):
                    local_kwargs[arg_name] = pos_args[i]
                else:
                    if kwargs.get(arg_name) is not None:
                        local_kwargs[arg_name] = kwargs[arg_name]

            s = method(current, **local_kwargs)
            if hasattr(s, 'as_list'):
                s = s.as_list()
            return s

        desc = MethodDesc(run_method_cb, method_args,
                          api_method=method,
                          doc=getattr(method, "__doc__", ""),
                          args_desc=getattr(method, "args", None))
        container[method_name] = desc
        prefix_components.append(method_name)

        self.methods.append(("/".join(prefix_components), desc))

    def call(self, current, api_method, *args, **kwargs):
        """This method is used for making internal API calls."""
        sep = "/" if "/" in api_method else "."
        call_args = [x for x in api_method.split(sep) if x]
        container = api_dispatcher.dispatch
        for arg in call_args:
            dispatch = container.get(arg)
            if dispatch is None:
                raise NotImplementedError(api_method)

            if isinstance(dispatch, dict):
                container = dispatch
                continue

            if isinstance(dispatch, MethodDesc):
                try:
                    # Mark this call as internal - csrf checking is disabled for
                    # internal calls.
                    current.session.internal_call = True
                    result = dispatch.run(current, args, kwargs)
                finally:
                    current.session.internal_call = False

                return result

    def run(self, current):
        container = api_dispatcher.dispatch
        for i, arg in enumerate(current.request.args):
            dispatch = container.get(arg)
            if dispatch is None:
                raise http.HTTP(404)

            if isinstance(dispatch, dict):
                container = dispatch
                continue

            if isinstance(dispatch, MethodDesc):
                current.response.headers['Content-Type'] = (
                    'application/json; charset=utf-8')
                try:
                    return current.response.json(
                        dispatch.run(current, current.request.args[i+1:],
                                     current.request.vars))
                except users.PermissionDenied as e:
                    current.response.status = 403
                    return dict(error="Permission Denied",
                                description="""
You do not have a required permission: %s on resource %s.
Please contact your administrator to be granted the required permission.""" % (
    e.permission, e.resource))

                except (ValueError, TypeError) as e:
                    current.response.status = 400
                    return dict(error=unicode(e), type="Invalid Arguments")

                except Exception as e:
                    logging.exception(
                        "While calling method %s.%s", dispatch.api_method.__module__,
                        dispatch.api_method)
                    current.response.status = 500
                    return dict(error=unicode(e), type=e.__class__.__name__)

        self.error()


api_dispatcher = APIDispatcher()


def discover(current):
    """List all the API endpoints and their known args."""
    result = []
    for method, desc in api_dispatcher.methods:
        result.append(dict(method=method,
                           doc=desc.doc,
                           args=desc.args_desc))

    return dict(data=result)

def require_csrf_token():
    def wrapper(current):
        # When authenticating without token, we must use CSRF protection. The
        # session mints a CSRF token which must be passed in the AJAX request as
        # well.
        token = current.request.vars.token

        # Note that token access is not CSRF protected.
        if not token and not current.session.internal_call:
            csrf_token = current.session.csrf_token
            if csrf_token != current.request.env["HTTP_X_REKALL_CSRF_TOKEN"]:
                raise users.PermissionDenied("An access token is required.")

        return True

    return wrapper


# We explicitly register all API plugins here in the one spot rather than use a
# plugin system where APIs are scattered in all plugins. We also explicitly
# declare the permissions required to access each API.
api_dispatcher.register("/list", discover,
                        [require_csrf_token(),
                         users.require_application("application.login")])

# Manage artifacts.
api_dispatcher.register("/artifacts/add", forensic_artifacts.add,
                        [require_csrf_token(),
                         users.require_application("artifacts.write")])

api_dispatcher.register("/artifacts/list", forensic_artifacts.list,
                        [require_csrf_token(),
                         users.require_application("artifacts.viewer")])

# Manage clients and access controls.
api_dispatcher.register("/client/search", client.search,
                        [require_csrf_token(),
                         users.require_application("clients.search")])

# The approval mechanism is used to promote a user with clients.search
# (i.e. Viewer) permission to clients.view permission (i.e. Examiner). Therefore
# Viewer is allowed to proceed with the approval flow, until they receive
# Examiner or Investigator on the client object.
api_dispatcher.register("/client/approver/list", client.list_approvers,
                        [require_csrf_token(),
                         users.require_application("clients.search")])

api_dispatcher.register("/client/approver/request", client.request_approval,
                        [require_csrf_token(),
                         users.require_application("clients.search")])

# Only users with an Approver role can grant an approval.
api_dispatcher.register("/client/approver/grant", client.approve_request,
                        [require_csrf_token(),
                         users.require_application("clients.approve")])

# Client controls.
api_dispatcher.register("/control/manifest", control.manifest,
                        [users.require_client_authentication()])
api_dispatcher.register("/control/startup", control.startup,
                        [users.require_client_authentication()])
api_dispatcher.register("/control/jobs", control.jobs,
                        [users.require_client_authentication()])
api_dispatcher.register("/control/ticket", control.ticket,
                        [users.require_client_authentication()])

api_dispatcher.register("/control/upload", control.upload,
                        [users.require_client_authentication()])

api_dispatcher.register("/control/upload_receive", control.upload_receive,
                        [users.anonymous_access()])

api_dispatcher.register("/control/file_upload", control.file_upload,
                        [users.require_client_authentication()])

# Query the server about plugins.
api_dispatcher.register("/plugin/list", plugins.list,
                        [require_csrf_token(),
                         users.require_application("application.login")])
api_dispatcher.register("/plugin/get", plugins.get,
                        [require_csrf_token(),
                         users.require_application("application.login")])

# Get information about collections for a specific client.
api_dispatcher.register("/collections/metadata", collections.metadata,
                        [require_csrf_token(),
                         users.require_client("clients.view")])

api_dispatcher.register("/collections/get", collections.get,
                        [require_csrf_token(),
                         users.require_client("clients.view")])


# Deal with flows. Must have at least Examiner access to the client.
api_dispatcher.register("/flows/list", flows.list,
                        [require_csrf_token(),
                         users.require_client("clients.view")])

api_dispatcher.register("/flows/download", flows.download,
                        [require_csrf_token(),
                         users.require_client("clients.view")])

api_dispatcher.register("/flows/make_canned", flows.make_canned_flow,
                        [require_csrf_token(),
                         users.require_client("clients.view")])

api_dispatcher.register("/flows/save_canned", flows.save_canned_flow,
                        [require_csrf_token(),
                         users.require_application("canned_flow.write")])

api_dispatcher.register("/flows/delete_canned", flows.delete_canned_flows,
                        [require_csrf_token(),
                         users.require_application("canned_flow.write")])

api_dispatcher.register("/flows/list_canned", flows.list_canned_flows,
                        [require_csrf_token(),
                         users.require_application("canned_flow.read")])

api_dispatcher.register("/flows/launch_canned", flows.launch_canned_flows,
                        [require_csrf_token(),
                         users.require_client("flows.create")])

# Only users with Investigator role can create new flows on the client.
api_dispatcher.register("/flows/plugins/launch", flows.launch_plugin_flow,
                        [require_csrf_token(),
                         users.require_client("flows.create")])


# File uploads.
api_dispatcher.register("/uploads/list", uploads.list,
                        [require_csrf_token(),
                         users.require_application("clients.view")])


# User Account management.
api_dispatcher.register("/users/list", users.list,
                        [require_csrf_token(),
                         users.require_admin()])

api_dispatcher.register("/users/add", users.add,
                        [require_csrf_token(),
                         users.require_admin()])

api_dispatcher.register("/users/delete", users.delete,
                        [require_csrf_token(),
                         users.require_admin()])

api_dispatcher.register("/users/roles/get", users.get_role,
                        [require_csrf_token(),
                         users.require_admin()])

# Anyone can list their own roles.
api_dispatcher.register("/users/roles/list", users.list_roles,
                        [require_csrf_token(),
                         users.require_application("application.login")])

api_dispatcher.register("/users/roles/my", users.my,
                        [require_csrf_token(),
                         users.require_application("application.login")])

# Only assigned delegators may mint tokens.
api_dispatcher.register("/users/tokens/mint", users.mint_token,
                        [require_csrf_token(),
                         users.require_application("token.mint")])


# Anyone can get their own notifications as long as they can use the app.
api_dispatcher.register("/users/notifications/count", users.count_notifications,
                        [require_csrf_token(),
                         users.require_application("application.login")])

api_dispatcher.register("/users/notifications/send", users.send_notifications,
                        [require_csrf_token(),
                         users.require_application("application.login")])

api_dispatcher.register("/users/notifications/read", users.read_notifications,
                        [require_csrf_token(),
                         users.require_application("application.login")])

api_dispatcher.register("/users/notifications/clear", users.clear_notifications,
                        [require_csrf_token(),
                         users.require_application("application.login")])
