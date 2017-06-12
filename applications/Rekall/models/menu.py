# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

# ----------------------------------------------------------------------------------------------------------------------
# Customize your APP title, subtitle and menus here
# ----------------------------------------------------------------------------------------------------------------------
from gluon.globals import current
from api import users


response.logo = A(IMG(_alt="Rekall Forensics", _class="logo",
                      _src=URL('static', 'images', 'Rekall Logo.svg')),
                  _class="navbar-brand", _href=URL(c="default", f="index"),
                  _id="logo")
response.title = request.application.replace('_', ' ').title()
response.subtitle = ''

# ----------------------------------------------------------------------------------------------------------------------
# read more at http://dev.w3.org/html5/markup/meta.name.html
# ----------------------------------------------------------------------------------------------------------------------
response.meta.author = myconf.get('app.author')
response.meta.description = myconf.get('app.description')
response.meta.keywords = myconf.get('app.keywords')
response.meta.generator = myconf.get('app.generator')

# ----------------------------------------------------------------------------------------------------------------------
# your http://google.com/analytics id
# ----------------------------------------------------------------------------------------------------------------------
response.google_analytics_id = None

# ----------------------------------------------------------------------------------------------------------------------
# this is the main application menu add/remove items as required
# ----------------------------------------------------------------------------------------------------------------------

response.menu = [
    (T('Dashboard'), False, URL('default', 'index'), []),
]


if users.check_permission(current, "clients.search", "/"):
    response.menu.append(
        (T('Clients'), False, '#', [
            (T('Search'), False, URL(c='clients', f='index'))
        ]))


# User is administrator - show them the users menu..
if users.check_permission(current, "users.admin", "/"):
    response.menu.append(
        (T('Users'), False, "#", [
            (T('Manage Users'), False, URL(c="users", f="manage")),
            (T('Add new User'), False, URL(c="users", f="add"))
        ]))


response.right_menu = [
    (users.get_current_username(), False, "#", [
        (T('Logout'), False, URL('default', 'logout'), []),
    ])
]
