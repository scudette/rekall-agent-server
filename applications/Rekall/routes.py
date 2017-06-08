# NOTE: Static files are handled in app.yaml

routes_in = (
    ('/', '/Rekall/default/index'),
    ('/Rekall/$anything', '/Rekall/$anything'),
    ('/api/$anything', '/Rekall/api/run/$anything'),
    ('/$c/$f$anything', '/Rekall/$c/$f$anything'),
    ('/static/$anything', '/Rekall/static/$anything'),
)

routes_out = [
    ('/Rekall/static/$anything', '/static/$anything'),
    ('/Rekall/api/run$anything', '/api$anything'),
    ('/Rekall/$c/$f$anything', '/$c/$f$anything'),
]
