# User and account management.
from api import utils

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
    return dict(form=form)
