"""An API controller for exposing controllers as API.

This is similar to the web2py Service() object.
"""
# This loads API plugins from Rekall/modules/api/...
from gluon import http

from api import client
from api import collections
from api import control
from api import flows
from api import plugins
from api import uploads
from api import users



class MethodDesc(object):
    """A descriptor for an API method."""

    def __init__(self, method, args):
        self.method = method
        self.args = args

    def run(self, current, args, kwargs):
        return self.method(current, args, kwargs)


class APIDispatcher(object):
    def __init__(self):
        self.dispatch = {}
        self.methods = []

    def error(self):
        raise http.HTTP(404, "Not Found")

    def register(self, path, method, security_manager=lambda x: True):
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
            security_manager(current)

            # We allow method args to be called as positional or keyword
            local_kwargs = {}
            for i, arg_name in enumerate(method_args):
                if i < len(pos_args):
                    local_kwargs[arg_name] = pos_args[i]
                else:
                    if kwargs.get(arg_name) is not None:
                        local_kwargs[arg_name] = kwargs[arg_name]

            if len(local_kwargs) < len(method_args):
                return dict(error="Not enough args provided.")

            s = method(current, **local_kwargs)
            if hasattr(s, 'as_list'):
                s = s.as_list()
            return s

        desc = MethodDesc(run_method_cb, method_args)
        container[method_name] = desc
        prefix_components.append(method_name)

        self.methods.append(("/".join(prefix_components), desc))

    def call(self, current, api_method, *args, **kwargs):
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
                return dispatch.run(current, args, kwargs)

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
                return current.response.json(
                    dispatch.run(current, current.request.args[i+1:],
                                 current.request.vars))

        self.error()


api_dispatcher = APIDispatcher()


def discover(_):
    """List all the API endpoints and their known args."""
    result = {}
    for method, desc in api_dispatcher.methods:
        result[method] = desc.args

    return result


# We explicitly register all API plugins here in the one spot rather than use a
# plugin system where APIs are scattered in all plugins. We also explicitly
# declare the permissions required to access each API.
api_dispatcher.register("/discover", discover,
                        users.require_application("clients.search"))

# Manage clients and access controls.
api_dispatcher.register("/client/search", client.search,
                        users.require_application("clients.search"))

# The approval mechanism is used to promote a user with clients.search
# (i.e. Viewer) permission to clients.view permission (i.e. Examiner). Therefore
# Viewer is allowed to proceed with the approval flow, until they receive
# Examiner or Investigator on the client object.
api_dispatcher.register("/client/approver/list", client.list_approvers,
                        users.require_application("clients.search"))

api_dispatcher.register("/client/approver/request", client.request_approval,
                        users.require_application("clients.search"))

# Only users with an Approver role can grant an approval.
api_dispatcher.register("/client/approver/grant", client.approve_request,
                        users.require_application("clients.approve"))

# Client controls.
api_dispatcher.register("/control/manifest", control.manifest,
                        users.require_client_authentication())
api_dispatcher.register("/control/startup", control.startup,
                        users.require_client_authentication())
api_dispatcher.register("/control/jobs", control.jobs,
                        users.require_client_authentication())
api_dispatcher.register("/control/ticket", control.ticket,
                        users.require_client_authentication())


# Query the server about plugins.
api_dispatcher.register("/plugin/list", plugins.list,
                        users.require_application("application.login"))
api_dispatcher.register("/plugin/get", plugins.get,
                        users.require_application("application.login"))

# Get information about collections for a specific client.
api_dispatcher.register("/collections/metadata", collections.metadata,
                        users.require_client("clients.view"))

api_dispatcher.register("/collections/get", collections.get,
                        users.require_client("clients.view"))


# Deal with flows. Must have at least Examiner access to the client.
api_dispatcher.register("/flows/list", flows.list,
                        users.require_client("clients.view"))

# Only users with Investigator role can create new flows on the client.
api_dispatcher.register("/flows/plugins/launch", flows.launch_plugin_flow,
                        users.require_client("flows.create"))


# File uploads.
api_dispatcher.register("/uploads/list", uploads.list,
                        users.require_application("clients.view"))


# User Account management.
api_dispatcher.register("/users/list", users.list,
                        users.require_admin())

api_dispatcher.register("/users/add", users.add,
                        users.require_admin())

api_dispatcher.register("/users/delete", users.delete,
                        users.require_admin())

api_dispatcher.register("/users/roles/get", users.get_role,
                        users.require_admin())

# Anyone can get their own notifications as long as they can use the app.
api_dispatcher.register("/users/notifications/count", users.count_notifications,
                        users.require_application("application.login"))

api_dispatcher.register("/users/notifications/send", users.send_notifications,
                        users.require_application("application.login"))

api_dispatcher.register("/users/notifications/read", users.read_notifications,
                        users.require_application("application.login"))

api_dispatcher.register("/users/notifications/clear", users.clear_notifications,
                        users.require_application("application.login"))
