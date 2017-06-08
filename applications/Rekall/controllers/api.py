"""An API controller for exposing controllers as API.

This is similar to the web2py Service() object.
"""
# This loads API plugins from Rekall/modules/api/...
from api import client
from api import collections
from api import control
from api import flows
from api import plugins
from api import uploads


class MethodDesc(object):
    """A descriptor for an API method."""

    def __init__(self, method, args):
        self.method = method
        self.args = args

    def run(self, args, kwargs):
        print args, kwargs
        return self.method(args, kwargs)


class APIDispatcher(object):
    def __init__(self):
        self.dispatch = {}
        self.methods = []

    def error(self):
        raise HTTP(404, "Not Found")

    def register(self, prefix, method):
        prefix_components = [x for x in prefix.split("/") if x]
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

        method_args = method_args[1:]

        def run_method_cb(pos_args, kwargs):
            """A controller function which will launched to handle the API."""
            response.headers['Content-Type'] = 'application/json; charset=utf-8'

            # We allow method args to be called as positional or keyword
            local_kwargs = {}
            for i, arg_name in enumerate(method_args):
                if i < len(pos_args):
                    local_kwargs[arg_name] = pos_args[i]
                else:
                    if kwargs[arg_name] is not None:
                        local_kwargs[arg_name] = kwargs[arg_name]

            s = method(current, **local_kwargs)
            if hasattr(s, 'as_list'):
                s = s.as_list()
            return s

        desc = MethodDesc(run_method_cb, method_args)
        container[method.__name__] = desc
        prefix_components.append(method.__name__)

        self.methods.append(("/".join(prefix_components), desc))

    def run(self):
        container = api_dispatcher.dispatch
        for i, arg in enumerate(request.args):
            dispatch = container.get(arg)
            if dispatch is None:
                raise HTTP(404)

            if isinstance(dispatch, dict):
                container = dispatch
                continue

            if isinstance(dispatch, MethodDesc):
                return response.json(
                    dispatch.run(request.args[i+1:], request.vars))

        self.error()


api_dispatcher = APIDispatcher()


def run():
    return api_dispatcher.run()


def discover(_):
    """List all the API endpoints and their known args."""
    result = {}
    for method, desc in api_dispatcher.methods:
        result[method] = desc.args

    return result


# We explicitly register all API plugins here.
api_dispatcher.register("/", discover)
api_dispatcher.register("/client", client.search)


# Client controls.
api_dispatcher.register("/control", control.manifest)
api_dispatcher.register("/control", control.startup)
api_dispatcher.register("/control", control.jobs)
api_dispatcher.register("/control", control.ticket)


# Query the server about plugins.
api_dispatcher.register("/plugin", plugins.list)
api_dispatcher.register("/plugin", plugins.get)

# Get information about collections.
api_dispatcher.register("/collections", collections.metadata)

# Deal with flows.
api_dispatcher.register("/flows", flows.list)

# File uploads.
api_dispatcher.register("/uploads", uploads.list)
