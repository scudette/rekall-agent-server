import uuid
import gluon
from gluon import html
from google.appengine.api import users


def new_hunt_id():
    return "H." + str(uuid.uuid4())[:16]


def new_collection_id():
    return "CL." + str(uuid.uuid4())[:16]


def new_flow_id():
    return "F." + str(uuid.uuid4())[:16]


def new_token_id():
    return "T." + str(uuid.uuid4())[:16]

def route_api(endpoint, *args, **kwargs):
    components = [x for x in endpoint.split("/") if x]
    components.extend(args)
    return gluon.URL(
        c="api", f=components[0], args=components[1:], vars=kwargs,
        host=True)


def build_form(inputs, with_submit=True, **kwargs):
    elements = []
    for input in inputs:
        input.attributes["_class"] = "form-control"
        name = input.attributes["_name"]

        if (input.attributes.get("_type") != "hidden"):
            elements.append(html.DIV(
                html.LABEL(name,
                           _class="col-sm-2 control-label",
                           _for=name),
                html.DIV(input, _class="col-sm-7"),
            _class="form-group"))
        else:
            elements.append(input);

    if with_submit:
        elements.append(html.INPUT(_type="submit",
                                   _id="submit",
                                   _role="button",
                                   _class="btn btn-default"))

    return html.FORM(*elements, _class="form-horizontal", **kwargs)


def BaseValueList(obj):
    res = []
    for x in obj:
        res.append(x.b_val)

    return res


def get_current_username(current):
    # If access was granted through a token, the username is the delegator.
    if current.request.token:
        return current.request.token["delegator"]

    user = users.get_current_user()
    if not user:
        return ""
    return user.email()
