
from flask import Flask
from .models import db


def create_app(name='cheztache', config=None):
    """
    Flask App factory

    :return: flask app
    """
    app = Flask(name)
    app.config.from_object('chez.tache.config.DefaultConfig')
    if config:
        app.config.from_object(config)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    return app
