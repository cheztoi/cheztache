
import os
from flask import Flask
from .models import db


def create_app(name='chez.tache', config=None):
    """
    Flask App factory

    :return: flask app
    """
    app = Flask(name)
    app.config.from_object('chez.tache.config.DefaultConfig')
    if config:
        app.config.from_object(config)

    root_directory = app.config['ROOT_DIRECTORY']
    if not os.path.exists(root_directory):
        os.makedirs(root_directory)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    return app
