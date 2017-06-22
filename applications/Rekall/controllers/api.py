from gluon.globals import current
import api


def run():
    """The main entry point for API access over HTTP."""
    response.view = "generic.json"

    return api.api_dispatcher.run(current)
