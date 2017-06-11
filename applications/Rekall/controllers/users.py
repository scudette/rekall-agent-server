# User and account management.
from gluon.globals import current
import api


def manage():
    return dict()


def add():
    """Add a new user role."""
    inputs = [INPUT(_name="user",
                    _class="form-control",
                    _title="User Email"),
              INPUT(_name="resource",
                    _class="form-control",
                    _title="Resource",
                    value="/"),
              SELECT(*sorted(users.roles),
                     _name="role",
                     _class="form-control",
                     requires=IS_IN_SET(users.roles)),
              ]

    elements = []
    for input in inputs:
        name = input.attributes["_name"]

        elements.append(DIV(
            LABEL(name,
                  _class="col-sm-2 control-label",
                  _for=name),
            DIV(input, _class="col-sm-7"),
            _class="form-group"))

    elements.append(INPUT(_type="submit"))

    form = FORM(*elements, _class="form-horizontal")
    if form.accepts(request, session):
        api.api_dispatcher.call(current, "users.add")

        redirect(URL(f="manage"))

    return dict(form=form)
