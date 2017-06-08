"""This part of the API is communicated directly with the client."""
import datetime

from rekall_lib.types import agent
from rekall_lib.types import client
from rekall_lib.types import location

import utils


def manifest(_):
    result = agent.Manifest.from_keywords(
        startup=dict(
            rekall_session=dict(live="API"),
            # Drop progress reports when running this flow.
            ticket=dict(location=location.DevNull()),
            actions=[
                client.StartupAction.from_keywords(
                    location=dict(
                        __type__="HTTPLocation",
                        base=utils.route_api("control/startup"),
                    )
                )
            ]))

    return result.to_primitive()


def startup(current):
    """Called in response to the startup flow issued by the manifest."""
    client_message = client.StartupMessage.from_json(
        current.request.body.getvalue())

    # Record the client event.
    current.db.client_logs.insert(client_id=client_message.client_id,
                          event='Startup',
                          data_type="StartupMessage",
                          data=client_message.to_primitive())

    current.db.clients.update_or_insert(
        current.db.clients.client_id == client_message.client_id,
        client_id=client_message.client_id,
        hostname=client_message.system_info.node,
        summary=client_message.to_primitive())

    return {}


def jobs(current, client_id=None, secret=None):
    """List all the jobs intended for this client."""
    db = current.db
    if client_id:
        result = agent.JobFile()
        for row in db(db.flows.client_id == client_id).select():
            # Send off newly schedules flows.
            if row.state == 'scheduled':
                db.flows[row.id] = dict(state='tasked')
                flow = agent.Flow.from_json(row.flow)
                result.flows.append(flow)

        row = db(db.clients.client_id == client_id).select().first()
        if row:
            db.clients[row.id] = dict(last=datetime.datetime.utcnow())

        return result.to_primitive()


def ticket(current, flow_id):
    db = current.db
    row = db(db.flows.flow_id == flow_id).select().first()
    if row:
        # Update the status from the client.
        status = agent.FlowStatus.from_json(current.request.body.getvalue())
        db.flows[row.id] = dict(status=status.to_primitive(),
                                state=status.status)

    return dict()
