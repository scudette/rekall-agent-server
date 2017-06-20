# @*- coding: utf-8 -*-
from api import users

from google.appengine.api import users as gae_users


def index():
    return dict()


def logout():
    logout_url = gae_users.create_login_url("/")
    return dict(logout_url=logout_url)


def api():
    """Provide an introspective view of the available APIs."""
    return dict()
