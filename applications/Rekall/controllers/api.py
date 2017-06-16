from gluon.globals import current
import api


def run():
    response.view = "generic.json"
    return api.api_dispatcher.run(current)
