# @*- coding: utf-8 -*-
from api import users

from google.appengine.api import users as gae_users


def index():
    form = FORM(INPUT(_name='q'), INPUT(_type='submit'))
    if form.accepts(request, session):
        redirect(URL(c="clients", f="index", vars=dict(q=form.vars.q)))

    return dict(form=form)


def logout():
    logout_url = gae_users.create_login_url("/")
    return dict(logout_url=logout_url)


def api():
    """Provide an introspective view of the available APIs."""
    return dict()
