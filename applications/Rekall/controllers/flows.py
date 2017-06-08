# Launch flows.
import json
import re
import os
import time
import uuid

from gluon.globals import current
from gluon import validators

from google.appengine.ext import blobstore

from rekall_lib.types import agent

import utils

from api import plugins


def list():
    client_id = request.vars.client_id
    if client_id:
        return dict(client_id=client_id)

    raise HTTP(400, "client_id must be provided.")


def inspect_list():
    client_id = request.vars.client_id
    return dict(client_id=client_id)


def uploads_view():
    flow_id = request.vars.flow_id
    return dict(flow_id=flow_id)


def hex_view():
    upload_id = request.vars.upload_id
    return dict(upload_id=upload_id)


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

        print "Unsupported arg %s: %s" % (arg, desc)

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
        type = desc['type']
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

        if type == "ChoiceArray" and set(value) == set(desc.get("default", [])):
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
                     session_inputs=session_inputs,
                     form=form)

    if form.accepts(request, session):
        response.flash = 'form accepted'
        plugin_arg = builder.ParseForm(form.vars)
        # Schedule the flow for the client.
        collection_id = unicode(uuid.uuid4())
        flow_id = unicode(uuid.uuid4())
        flow = agent.Flow.from_keywords(
            flow_id=flow_id,
            created_time=time.time(),
            rekall_session=dict(live="API"),
            file_upload=dict(
                __type__="FileUploadLocation",
                flow_id=flow_id,
                base=URL(c="control", f='file_upload', host=True)),
            ticket=dict(
                location=dict(
                    __type__="HTTPLocation",
                    base=utils.route_api('/control/ticket'),
                    path_prefix=flow_id,
                )),
            actions=[
                dict(__type__="PluginAction",
                     plugin=plugin,
                     args=builder.ParseForm(form.vars),
                     collection=dict(
                         __type__="JSONCollection",
                         id=collection_id,
                         location=dict(
                             __type__="BlobUploader",
                             base=URL(
                                 c="control", f='upload', host=True),
                             path_template=(
                                 "collection/%s/{part}" % collection_id),
                         ))
                )])

        db.flows.insert(
            flow_id=flow_id,
            client_id=client_id,
            flow=flow.to_primitive(),
        )

        db.collections.insert(
            collection_id=collection_id,
            flow_id=flow_id)

        view_args["launched"] = True
        view_args["plugin_arg"] = plugin_arg

    print view_args
    return dict(**view_args)


def collection():
    """Stream the requested collection.

    Note that we do not edit the collection in any way we just stream the same
    thing the client sent to us. We rely on AppEngine's automatic blob store
    detection to stream the data from blob store by setting the right header in
    the response.
    """
    try:
        collection_id = request.args[0]
        if len(request.args) == 1:
            part = 0
        else:
            part = int(request.args[1])

    except (ValueError, IndexError) as e:
        raise HTTP(400, "collection_id must be provided.")

    row = db(db.collections.collection_id == collection_id).select().first()
    if row:
        row = db((db.collections.collection_id == collection_id) &
                 (db.collections.part == part)).select().first()

        if row:
            response.headers[blobstore.BLOB_KEY_HEADER] = row.blob_key
            response.headers["Content-Type"] = "application/json"
        else:
            raise HTTP(404, "collection not found")


def download():
    upload_id = request.vars.upload_id
    filename = request.vars.filename or "download_" + upload_id
    if upload_id:
        row = db(db.uploads.id == upload_id).select().first()
        if row:
            response.headers[blobstore.BLOB_KEY_HEADER] = row.blob_key
            response.headers["Content-Type"] = "application/octet-stream"
            response.headers["Content-Disposition"] = (
                'attachment; filename="%s"' % xmlescape(filename))
        else:
            raise HTTP(404, "not found")


def collection_view():
    """Render the collection.

    Note the actual data is streamed from Blobstore. This controller just
    creates the viewing page.
    """
    try:
        collection_id = request.args[0]
        if len(request.args) == 1:
            part = 0
        else:
            part = int(request.args[1])

    except (ValueError, IndexError) as e:
        raise HTTP(400, "collection_id must be provided.")

    return dict(collection_id=collection_id, part=part)
