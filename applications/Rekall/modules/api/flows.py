"""API implementations for interacting with flows."""
import re
import time

from gluon import html
from rekall_lib.types import actions
from rekall_lib.types import agent

import api

from api import audit
from api import firebase
from api import plugins
from api import users
from api import utils


def describe(current, flow_id, client_id):
    """Describe information about the flow."""
    db = current.db
    row = db(db.flows.flow_id == flow_id).select().first()
    if row and row.client_id == client_id:
        collection_ids = [
            x.collection_id for x in
            db(db.collections.flow_id == flow_id).select()]

        file_infos = []
        for x in db(db.upload_files.flow_id == flow_id).select():
            file_infos.append(dict(
                upload_id=x.upload_id,
                file_information=x.file_information.to_primitive()))

        return dict(
            flow=row.flow.to_primitive(),
            creator=row.creator,
            timestamp=row.timestamp,
            status=row.status.to_primitive(),
            collection_ids=collection_ids,
            file_infos=file_infos)

    raise IOError("Flow %s not found" % flow_id)


def list_flows(current, client_id):
    """Inspect all the launched flows."""
    flows = []
    db = current.db
    if client_id:
        for row in db(db.flows.client_id == client_id).select(
            orderby=~db.flows.timestamp
        ):
            flows.append(dict(
                flow=row.flow.to_primitive(),
                timestamp=row.timestamp,
                creator=row.creator,
                status=row.status.to_primitive(),
            ))

    return dict(data=flows)

def assert_in_choices(name, choices, value):
    for choice in choices:
        if value == choice:
            return

    raise ValueError("Values for %s must be in %s" % (name, choices))

def assert_is_list(name, value):
    if not isinstance(value, list):
        raise ValueError("Value for %s must be a list." % name)

def assert_is_string(name, value):
    if not isinstance(value, basestring):
        raise ValueError("Value for %s must be a string." % name)

def convert_to_int(name, value):
    try:
        return long(value, 0)
    except ValueError:
        raise ValueError("Value for %s must be an integer (got %s)." % (
            name, value))


def convert_boolean(name, value):
    if value in ["true", "on"]:
        value = True
    elif value in ["false", "", "off"]:
        value = False
    else:
        raise ValueError("Value for %s must be boolean." % name)

    return value


def validate_plugin_args(plugin_arg, spec):
    """Ensures that plugin_arg follows the spec."""
    for arg, desc in spec["args"].iteritems():
        if arg not in plugin_arg:
            continue

        type = desc["type"]
        value = plugin_arg[arg]
        if type == "ChoiceArray":
            assert_is_list(arg, value)
            if not value:
                del plugin_arg[arg]
                continue

            for sub_value in value:
                assert_in_choices(arg, desc["choices"], sub_value)

        elif type == "Choice":
            assert_in_choices(arg, desc["choices"], value)

        elif type == "String":
            if "choices" in desc:
                assert_in_choices(arg, desc["choices"], value)

            # Remove empty values.
            if value == "":
                del plugin_arg[arg]

        elif type == "IntParser":
            # Remove empty values.
            if value == "":
                del plugin_arg[arg]
            else:
                plugin_arg[arg] = convert_to_int(arg, value)

        elif type in ["ArrayStringParser", "ArrayString"]:
            assert_is_list(arg, value)
            # Remove empty lists.
            if not value:
                del plugin_arg[arg]
                continue

            for sub_value in value:
                assert_is_string(arg, sub_value)

        elif type == "RegEx":
            # Remove empty entries.
            if not value:
                del plugin_arg[arg]
                continue

            try:
                re.compile(value)
            except Exception as e:
                raise ValueError("Value for %s must be a valid regex: %s" % (
                    arg, e))

        elif type == "ArrayIntParser":
            assert_is_list(arg, value)
            # Remove empty lists.
            if not value:
                del plugin_arg[arg]
                continue

            converted_list = []
            for sub_value in value:
                if sub_value == "":
                    continue

                converted_list.append(convert_to_int(arg, sub_value))

            plugin_arg[arg] = converted_list

        elif type == "Boolean":
            # Remove empty lists.
            if not value:
                del plugin_arg[arg]
                continue

            plugin_arg[arg] = convert_boolean(arg, value)


def launch_plugin_flow(current, client_id, rekall_session, plugin, plugin_arg):
    """Launch the flow on the client."""
    db = current.db
    flow_id = utils.new_flow_id()
    spec = plugins.RekallAPI(current).get(plugin)
    if not spec:
        raise ValueError("Unknown plugin")

    # Validate both plugin args and session args.
    validate_plugin_args(plugin_arg, spec)
    validate_plugin_args(rekall_session, plugins.SessionAPI(current))

    flow = agent.Flow.from_keywords(
        flow_id=flow_id,
        created_time=time.time(),
        ticket=dict(
            location=dict(
                __type__="HTTPLocation",
                base=utils.route_api('/control/ticket'),
                path_prefix=flow_id,
            )),
        actions=[
            dict(__type__="PluginAction",
                 plugin=plugin,
                 args=plugin_arg,
                 rekall_session=rekall_session,
                 collection=dict(
                     __type__="JSONCollection",
                     location=dict(
                         __type__="BlobUploader",
                         base=html.URL(
                             c="api", f="control", args=['upload'], host=True),
                         path_template=(
                             "collection/%s/{part}" % flow_id),
                     ))
            )])

    if rekall_session.get("also_upload_files"):
        flow.file_upload = dict(
            __type__="FileUploadLocation",
            flow_id=flow_id,
            base=html.URL(c="api", f='control/file_upload',
                          host=True))

    db.flows.insert(
        flow_id=flow_id,
        client_id=client_id,
        status=agent.FlowStatus.from_keywords(
            timestamp=time.time(),
            client_id=client_id,
            flow_id=flow_id,
            status="Pending"),
        creator=utils.get_current_username(current),
        flow=flow,
        timestamp=flow.created_time.timestamp,
    )

    firebase.notify_client(client_id)

    audit.log(current, "FlowLaunchPlugin", flow_id=flow_id, plugin=plugin,
              client_id=client_id)

    return {}


def make_canned_flow(current, flow_ids, client_id):
    """Merge the flow ids into a single canned flow."""
    result = agent.CannedFlow()
    db = current.db
    seen = set()
    for flow_id in flow_ids:
        row = db(db.flows.flow_id == flow_id).select().first()
        if row and row.client_id == client_id:
            for action in row.flow.actions:
                if isinstance(action, actions.PluginAction):
                    canned_action = actions.PluginAction.from_keywords(
                        plugin=action.plugin,
                        rekall_session=action.rekall_session,
                        args=action.args)

                    # Dedupe identical canned actions.
                    key = canned_action.to_json()
                    if key in seen:
                        continue

                    seen.add(key)
                    result.actions.append(canned_action)

    return result.to_primitive()


def save_canned_flow(current, canned_flow):
    canned = agent.CannedFlow.from_json(canned_flow)
    db = current.db
    if not canned.name or not canned.category:
        raise ValueError(
            "Canned flows must have a name, and category")

    # Check to see if there is a canned flow of the same name:
    row = db(db.canned_flows.name == canned.name).select().first()
    if row:
        raise ValueError("There is already a canned flow with name '%s'" %
                         canned.name)

    db.canned_flows.insert(
        name=canned.name,
        description=canned.description,
        category=canned.category,
        flow=canned)

    return canned.to_primitive()

def list_canned_flows(current):
    db = current.db
    result = []
    for row in db(db.canned_flows.id > 0).select():
        result.append(row.flow.to_primitive())

    return dict(data=result)

def delete_canned_flows(current, names=None):
    db = current.db
    for name in names or []:
        db(db.canned_flows.name == name).delete()

    return {}


def launch_canned_flows(current, client_id, name):
    db = current.db
    row = db(db.canned_flows.name == name).select().first()
    if not row:
        raise ValueError("There is no canned flow with name '%s'" % name)

    also_upload_files = False
    flow_id = utils.new_flow_id()
    for action in row.flow.actions:
        if action.rekall_session.get("also_upload_files"):
            also_upload_files = True
        action.collection = dict(
            __type__="JSONCollection",
            location=dict(
                __type__="BlobUploader",
                base=html.URL(
                    c="api", f="control", args=['upload'], host=True),
                path_template=(
                    "collection/%s/{part}" % flow_id),
            ))

    flow = agent.Flow.from_keywords(
        name=name,
        flow_id=flow_id,
        created_time=time.time(),
        ticket=dict(
            location=dict(
                __type__="HTTPLocation",
                base=utils.route_api('/control/ticket'),
                path_prefix=flow_id,
            )),
        actions=row.flow.actions,
    )

    if also_upload_files:
        flow.file_upload = dict(
            __type__="FileUploadLocation",
            flow_id=flow_id,
            base=html.URL(c="api", f='control/file_upload',
                          host=True))

    db.flows.insert(
        flow_id=flow_id,
        client_id=client_id,
        status=agent.FlowStatus.from_keywords(
            timestamp=time.time(),
            client_id=client_id,
            flow_id=flow_id,
            status="Pending"),
        creator=utils.get_current_username(current),
        flow=flow,
        timestamp=flow.created_time.timestamp,
    )

    firebase.notify_client(client_id)

    audit.log(current, "FlowLaunchCanned", flow_id=flow_id, canned_flow=name,
              client_id=client_id)

    return {}


def download(current, flow_ids, client_id):
    """Allow downloading of the flows, their results."""
    if isinstance(flow_ids, basestring):
        flow_ids = [flow_ids]

    db = current.db
    result = []
    grants = {}
    for row in db(db.flows.flow_id.belongs(flow_ids)).select():
        token = grants.get(row.client_id)
        if token is None:
            # Only show the flows from clients that the caller is authorized
            # for.
            if users.check_permission(
                current, "clients.view", "/" + row.client_id):
                token = users.mint_token(
                    current, "Examiner", "/" + row.client_id)["token"]
            else:
                token = ""

            grants[row.client_id] = token
        if token:
            flow_id = row.flow_id
            file_infos = []
            # Get all uploaded files.
            for x in db(db.upload_files.flow_id == flow_id).select():
                file_infos.append(dict(
                    upload_id=x.upload_id,
                    file_information=x.file_information.to_primitive()))

            # Get all collections.
            collection_ids = [
                x.collection_id for x in
                db(db.collections.flow_id == flow_id).select()]

            result.append(dict(name=row.flow_id,
                               flow=row.flow.to_primitive(),
                               client_id=row.client_id,
                               collection_ids=collection_ids,
                               file_infos=file_infos,
                               token=token,
                               status=row.status.to_primitive()))

    return dict(data=result)


def list_labels(current):
    db = current.db
    result = set()
    for row in db(db.labels).select():
        result.add(row.name)

    return dict(data=sorted(result))
