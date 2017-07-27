# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

# ----------------------------------------------------------------------------------------------------------------------
# Customize your APP title, subtitle and menus here
# ----------------------------------------------------------------------------------------------------------------------
import api
from api import users
from api import utils
import logging

from gluon.globals import current
from gluon import http


def InitializeMenu():
    """Build the menu bar.

    Depending on permissions different options are visible.
    """
    response.logo = A(IMG(_alt="Rekall Forensics", _class="logo",
                          _src=URL('static', 'images', 'Rekall Logo.svg')),
                      _class="navbar-brand web2py-menu-active link",
                      _href=URL(c="default", f="index"), _id="logo")
    response.title = request.application.replace('_', ' ').title()
    response.subtitle = ''

    response.meta.author = "The Rekall Team"
    response.meta.description = "The Rekall Agent Server"
    response.meta.keywords = "Rekall, Forensics"

    if users.check_permission(current, "clients.search", "/"):
        response.menu.append(
            (T('Clients'), False, dict(_href="#", _id="client_lru"), [
                (T('-'), False, None),
            ]))

    response.menu.append(
        (T('Artifacts'), False, "#", [
            (T('Manage Artifacts'), True, URL(c='artifacts', f='index')),
            (T('Precanned Flows'), True, URL(c='flows', f='list_canned')),
        ]))

    response.menu.append(
        (T("Hunts"), True, URL(c="hunts", f="view")))

    # User is administrator - show them the users menu..
    if users.check_permission(current, "users.admin", "/"):
        response.menu.append(
            (T('Users'), True, URL(c="users", f="manage")))

    # Only app admins can access the raw DB.
    if users.is_user_app_admin():
        response.menu.append(
            (T('DB'), False, URL(c="appadmin", f="manage")),
        )

    if users.check_permission(current, "audit.read", "/"):
        response.menu.append(
            (T('Audit'), True, URL(c="audit", f="search")))

    response.menu.append(
        (T('Api'), True, URL(c="default", f="api")))

    response.right_menu = [
        (utils.get_current_username(current), False, "#", [
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


# If the request comes with the bare header, we do not render the template. This
# is useful to be able to render into the main viewport with ajax calls, while
# at the same time maintaining proper URLs for page refresh.
if request.env["HTTP_X_REKALL_BARE_LAYOUT"]:
    response.layout_path = "layout_bare.html"
else:
    response.layout_path = "layout.html"
