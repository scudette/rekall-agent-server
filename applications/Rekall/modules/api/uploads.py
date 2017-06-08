import json

def list(current, flow_id):
    uploads = []
    db = current.db
    if flow_id:
        for row in db(db.upload_files.flow_id == flow_id).select():
            uploads.append(dict(
                file_information=json.loads(row.file_information),
                upload_id=row.upload_id))

    return dict(data=uploads)
