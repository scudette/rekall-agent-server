"""Methods for accessing clients."""
import json
import gluon

def search(current, query=None):
    if not query:
        raise gluon.HTTP(400, "query must be provided.")

    query = query.strip()
    condition = current.db.clients.id > 0

    # Search for a client ID directly.
    if query.startswith("C."):
        condition = current.db.clients.client_id == query
    else:
        # AppEngine uses Bigtable which does not support `like` operation. We
        # only support a prefix match.
        condition = ((current.db.clients.hostname >= query) &
                     (current.db.clients.hostname < query + u"\ufffd"))

    result = []
    for row in current.db(condition).select():
        result.append(dict(
            last=row.last,
            flows_link=gluon.URL(
                c='flows', f='inspect_list',
                vars=dict(client_id=row.client_id)),
            summary=json.loads(row.summary)))

    return dict(data=result)
