# @*- coding: utf-8 -*-

def index():
    form = FORM(INPUT(_name='q'), INPUT(_type='submit'))
    if form.accepts(request, session):
        redirect(URL(c="clients", f="index", vars=dict(q=form.vars.q)))

    return dict(form=form)
