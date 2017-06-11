# @*- coding: utf-8 -*-
from api import users

from google.appengine.api import users as gae_users


@users.require(current, "application.login")
def index():
    form = FORM(INPUT(_name='q'), INPUT(_type='submit'))
    if form.accepts(request, session):
        redirect(URL(c="clients", f="index", vars=dict(q=form.vars.q)))

    return dict(form=form)


def logout():
    logout_url = gae_users.create_logout_url("/")
    return dict(logout_url=logout_url)
