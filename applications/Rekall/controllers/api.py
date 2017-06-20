from gluon.globals import current
import api


def run():
    """The main entry point for API access over HTTP."""
    response.view = "generic.json"

    # When authenticating without token, we must use CSRF protection. The
    # session mints a CSRF token which must be passed in the AJAX request as
    # well.
    token = current.request.vars.token

    # Note that token access is not CSRF protected.
    if not token:
        csrf_token = current.session.csrf_token
        if csrf_token != current.request.env["HTTP_X_REKALL_CSRF_TOKEN"]:
            raise HTTP(403, "An access token is required.")

    return api.api_dispatcher.run(current)
