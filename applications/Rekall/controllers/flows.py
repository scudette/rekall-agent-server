# Launch flows.
import re

from gluon.globals import current
from gluon import http
from gluon import validators

from google.appengine.ext import blobstore

import api


from api import plugins

def description():
    client_id = request.vars.client_id
    flow_id = request.vars.flow_id
    if client_id and flow_id:
        return dict(client_id=client_id,
                    flow_id=flow_id)

def list():
    client_id = request.vars.client_id
    if client_id:
        return dict(client_id=client_id)

    raise HTTP(400, "client_id must be provided.")


def inspect_list():
    client_id = request.vars.client_id
    return dict(client_id=client_id)


def hex_view():
    upload_id = request.vars.upload_id
    offset = request.vars.offset or 0
    return dict(upload_id=upload_id, offset=offset)


def list_canned():
    return dict()


class CommaSeparated(validators.Validator):
    """A validator which converts comma separated string to a list."""

    def __init__(self, separator, validator=unicode):
        self.validator = validator
        self.separator = separator

    def __call__(self, value):
        result = []
        for x in value.split(self.separator):
            x = x.strip()
            if x == '':
                continue

            try:
                x = self.validator(x)
                result.append(x)
            except Exception as e:
                return None, "Invalid value: %s" % unicode(x)

        # Remove empty strings.
        return result, None


class RegexValidator(validators.Validator):
    def __init__(self, error_message="Not a valid Regular Expression"):
        self.error_message = error_message

    def __call__(self, value):
        try:
            re.compile(value)
        except Exception as e:
            return None, validators.translate(self.error_message)

        return value, None


class FormBuilder(object):
    def __init__(self, api_info, with_hidden=True):
        self.with_hidden = with_hidden
        self.api_info = api_info

    def BuildInput(self, arg, desc):
        type = desc.get('type', 'String')
        if type == "ChoiceArray":
            return SELECT(*desc['choices'],
                          _name=arg,
                          _id=arg,
                          _multiple=True,
                          _class="form-control",
                          requires=IS_IN_SET(desc['choices'], multiple=True),
                          value=desc.get('default', []))

        if type == "Choice":
            return SELECT(*desc['choices'],
                          _name=arg,
                          _id=arg,
                          _multiple=False,
                          _class="form-control",
                          requires=IS_IN_SET(desc['choices'], multiple=True),
                          value=desc.get('default', []))

        if type == 'String':
            if "choices" in desc:
                return SELECT(*desc['choices'],
                              _name=arg,
                              _id=arg,
                              _class="form-control",
                              requires=IS_IN_SET(desc['choices']),
                              value=desc.get('default', []))
            return INPUT(_name=arg,
                         _id=arg,
                         _class="form-control",
                         _title="A string required")

        if type == 'Boolean':
            return DIV(INPUT(_name=arg,
                             _id=arg,
                             _class="form-control",
                             _type='checkbox'),
                       _class="form-group-sm")

        if type == 'IntParser':
            return INPUT(
                    _id=arg,
                    _title="Integer required",
                    _placeholder=desc.get("default"),
                    _class="form-control",
                    _name=arg, requires=IS_EMPTY_OR(
                            IS_INT_IN_RANGE(0, 2**64, "Must be an integer")))

        if type in ("ArrayStringParser", "ArrayString"):
            return INPUT(
                    _id=arg,
                    _title="Comma separated list of strings.",
                    _class="form-control",
                    _name=arg, requires=CommaSeparated(",", unicode))

        if type == "ArrayIntParser":
            return INPUT(
                    _id=arg,
                    _title="Comma separated list of integers.",
                    _class="form-control",
                    _name=arg, requires=CommaSeparated(",", long))

        if type == "RegEx":
            return INPUT(
                    _id=arg,
                    _title="Regular expression expected",
                    _class="form-control",
                    _name=arg, requires=RegexValidator())

    def Build(self):
        inputs = []
        for arg, desc in sorted(
                self.api_info.get('args', {}).iteritems()):
            if desc.get("hidden") and not self.with_hidden:
                continue

            input = self.BuildInput(arg, desc)
            if input is not None:
                inputs.append(DIV(
                        LABEL(arg, _class="col-sm-2 control-label",
                              _for=arg,
                              _title=desc.get('help', '')),
                        DIV(input, _class="col-sm-7"),
                        _class="form-group",
                ))

        return inputs

    def ParseValue(self, value, desc):
        if value is None:
            return value

        type = desc.get('type', "String")
        if type == 'Boolean':
            state = value == "on"
            if state == desc.get('default', False):
                return

            return state

        # Empty strings are omitted.
        if type in ("String", "RegEx") and value == "":
            return

        if type in ("ArrayStringParser", "ArrayIntParser") and not value:
            return

        if type == "ChoiceArray" and set(value) == set(desc.get("default") or []):
            return

        return value

    def ParseForm(self, vars):
        result = {}
        for arg, desc in self.api_info.get('args', {}).iteritems():
            value = self.ParseValue(vars.get(arg), desc)
            if value is not None:
                result[arg] = value

        return result


class SessionFormBuilder(FormBuilder):

    default_session_parameters = dict(
        flow_precondition="",
        also_upload_files=False,
        cpu_quota=60,
        load_quota=50,
        verbose=False,
        live="API",
        autodetect=["windows_kernel_file", "linux_index", "osx"]
    )

    def Build(self):
        inputs = []
        for desc in sorted(self.api_info, key=lambda x: x["name"]):
            arg = desc["name"]
            if not self.with_hidden:
                if desc.get("hidden"):
                    continue

                if arg not in self.default_session_parameters:
                    continue

                desc["default"] = self.default_session_parameters[arg]

            input = self.BuildInput("session_" + arg, desc)
            if input is not None:
                inputs.append(DIV(
                    LABEL(arg, _class="col-sm-2 control-label",
                          _for=arg,
                          _title=desc.get('help', '')),
                    DIV(input, _class="col-sm-7"),
                    _class="form-group",
                ))

        return inputs

    def ParseForm(self, vars):
        result = {}
        for desc in self.api_info:
            name = desc["name"]
            value = self.ParseValue(vars.get("session_" + name), desc)
            if value is not None:
                result[name] = value

        return result


def launch():
    plugin = request.vars.plugin
    client_id = request.vars.client_id
    if not plugin or not client_id:
        session.flash = T("Invalid plugin name")
        raise HTTP(400, "client_id must be provided.")

    api_info = plugins.get(current, plugin)
    builder = FormBuilder(
        api_info, with_hidden=request.vars.with_hidden)
    session_builder = SessionFormBuilder(
        plugins.SessionAPI(current),
        with_hidden=request.vars.with_hidden)

    inputs = builder.Build()
    session_inputs = session_builder.Build()

    form = FORM(*(inputs + session_inputs))
    view_args = dict(plugin=plugin, client_id=client_id,
                     inputs=inputs, api_info=api_info,
                     launched=False, plugin_arg=None,
                     error=None,
                     session_inputs=session_inputs,
                     form=form)

    if form.accepts(request, session):
        plugin_arg = builder.ParseForm(form.vars)
        rekall_session = session_builder.ParseForm(form.vars)

        # The actual flow scheduling is done via the API.
        try:
            api.api_dispatcher.call(
                current, "flows.plugins.launch",
                client_id, rekall_session, plugin, plugin_arg)
        except http.HTTP as e:
            # Permission denied errors require approval.
            view_args["error"] = e

        return http.redirect(
            URL(f="inspect_list", vars=dict(client_id=client_id)))

    return dict(**view_args)


def collection_view():
    """Render the collection.

    Note the actual data is streamed from Blobstore. This controller just
    creates the viewing page.
    """
    part = request.vars.part or 0
    if request.vars.collection_id:
        return dict(collection_id=request.vars.collection_id,
                    client_id=request.vars.client_id,
                    part=part)


def save():
    flows = []
    flow_ids = request.vars.flows
    if flow_ids:
        for flow_id in flow_ids:
            row = db(db.flows.flow_id == flow_id).select().first()
            if row:
                flows.append(row.flow.to_primitive())

    return dict(flows=flows)
