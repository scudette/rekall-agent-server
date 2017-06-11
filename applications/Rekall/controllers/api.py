from gluon.globals import current
import api

def run():
    return api.api_dispatcher.run(current)
