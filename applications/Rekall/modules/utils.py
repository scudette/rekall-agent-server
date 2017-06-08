import gluon


def route_api(endpoint, *args, **kwargs):
    components = [x for x in endpoint.split("/") if x]
    components.extend(args)
    return gluon.URL(
        c="api", f=components[0], args=components[1:], vars=kwargs,
        host=True)
