try:
    from functools import lru_cache
except ImportError:
    from functools32 import lru_cache

import uuid

import json
import hashlib
import logging

import httplib2


from oauth2client.client import GoogleCredentials
_FIREBASE_SCOPES = [
    'https://www.googleapis.com/auth/firebase.database',
]

# TODO: This should be set in the config file.
database_url = "https://fourth-carport-147912.firebaseio.com"


@lru_cache()
def _get_http():
    """Provides an authed http object."""
    http = httplib2.Http()
    # Use application default credentials to make the Firebase calls
    # https://firebase.google.com/docs/reference/rest/database/user-auth
    creds = GoogleCredentials.get_application_default().create_scoped(
        _FIREBASE_SCOPES)
    creds.authorize(http)
    return http


def notify_client(client_id):
    """Push a notification to the real time database.

    Note that the client does not actually read this - it is just notified when
    it changes making it check the real API endpoint for pending flows. The
    firebase database is set up with the following rules (permissions):

    {
      "rules": {
        ".read": "true",
        ".write": "auth != null",
      }
    }

    i.e. anonymous read and authenticated write. Since the content does not
    matter we just write a uuid on it.
    """
    url = "%s/clients/%s.json" % (database_url, hashlib.sha1(
        client_id).hexdigest())
    try:
        response, content = _get_http().request(
            url, method='PUT', body=json.dumps(dict(uuid=str(uuid.uuid4()))))

        if response.status != 200:
            raise  IOError(response.content)

    except Exception as e:
        # Firebase is best effort only.
        logging.warning("Unable to contact firebase: %s", e)
