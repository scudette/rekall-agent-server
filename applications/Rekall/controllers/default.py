# @*- coding: utf-8 -*-
import api as api_module
from api import config
from api import users
from api import utils

from google.appengine.api import users as gae_users


def index():
    return dict()


def logout():
    logout_url = gae_users.create_login_url("/")
    return dict(logout_url=logout_url, demo=config.GetConfig(current).demo)


def api():
    """Provide an introspective view of the available APIs."""
    return dict()


def demo():
    return dict(login_url=gae_users.create_login_url("/"))


def call():
    """Render a form that allows the user to call the API."""
    method = request.vars.method
    for desc in api_module.api_dispatcher.call(current, "/list")["data"]:
        if desc["method"] == method:
            inputs = [INPUT(_name=x, _value=request.vars[x])
                      for x in desc["args"]]
            return dict(method="/" + method,
                        form=utils.build_form(
                            inputs, with_submit=False, method="POST"))
