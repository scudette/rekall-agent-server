# Controller to manage clients.
import json

def index():
    form = FORM('Search:', INPUT(_name='q'), INPUT(_type='submit'))
    form.accepts(request, session)
    return dict(form=form)
