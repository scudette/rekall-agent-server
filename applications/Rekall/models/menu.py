# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

# ----------------------------------------------------------------------------------------------------------------------
# Customize your APP title, subtitle and menus here
# ----------------------------------------------------------------------------------------------------------------------
import api
from api import users

from gluon.globals import current
from gluon import http


def InitializeMenu():
    """Build the menu bar.

    Depending on permissions different options are visible.
    """
    response.logo = A(IMG(_alt="Rekall Forensics", _class="logo",
                          _src=URL('static', 'images', 'Rekall Logo.svg')),
                      _class="navbar-brand", _href=URL(c="default", f="index"),
                      _id="logo")
    response.title = request.application.replace('_', ' ').title()
    response.subtitle = ''

    response.meta.author = myconf.get('app.author')
    response.meta.description = myconf.get('app.description')
    response.meta.keywords = myconf.get('app.keywords')
    response.meta.generator = myconf.get('app.generator')

    response.menu = [
        (T('Dashboard'), False, URL('default', 'index'), []),
    ]

    if users.check_permission(current, "clients.search", "/"):
        response.menu.append(
            (T('Clients'), False, '#', [
                (T('Search'), False, URL(c='clients', f='index'))
            ]))

    if request.vars.client_id:
        try:
            client_information = api.api_dispatcher.call(
                current, "/client/search", request.vars.client_id)["data"]
            if client_information:
                client_information = client_information[0]
                try:
                    client_name = client_information["summary"]["system_info"]["fqdn"]
                except KeyError:
                    client_name = request.vars.client_id

                response.menu[-1][3].append(
                    (client_name, False,
                     A(client_name,
                       _onclick="rekall.clients.show_info('%s');" % (
                           request.vars.client_id))))
        except http.HTTP:
            pass


    response.menu.append(
        (T('Artifacts'), False, URL(c='artifacts', f='index')))


    # User is administrator - show them the users menu..
    if users.check_permission(current, "users.admin", "/"):
        response.menu.append(
            (T('Users'), False, "#", [
                (T('Manage Users'), False, URL(c="users", f="manage")),
                (T('Add new User'), False, URL(c="users", f="add"))
            ]))

    # Only app admins can access the raw DB.
    if users.is_user_app_admin():
        response.menu.append(
            (T('DB'), False, URL(c="appadmin", f="manage")),
        )

    response.menu.append(
        (T('Api'), False, URL(c="default", f="api")))

    response.right_menu = [
        (users.get_current_username(), False, "#", [
            (T('Logout'), False, URL('default', 'logout'), []),
        ])
    ]


# This page is always visible to everyone.
if (request.controller, request.function) == ("default", "logout"):
    request.menu = []

# API access has its own ACL mechanism.
elif request.controller == "api":
    pass

# Check the user has permission to access this page,
elif not users.check_permission(current, "application.login", "/"):
    redirect(URL(c="default", f="logout"))

else:
    InitializeMenu()
