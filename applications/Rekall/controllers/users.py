# User and account management.
from gluon.globals import current
import api
import utils

def manage():
    return dict()


def add():
    """Add a new user role."""
    inputs = [INPUT(_name="user",
                    _title="User Email"),
              INPUT(_name="resource",
                    _title="Resource",
                    value="/"),
              SELECT(*sorted(users.roles),
                     _name="role",
                     requires=IS_IN_SET(users.roles)),
              ]

    form = utils.build_form(inputs)
    if form.accepts(request, session):
        api.api_dispatcher.call(current, "users.add")

        redirect(URL(f="manage"))

    return dict(form=form)
