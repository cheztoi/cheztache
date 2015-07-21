
from flask import Flask
from .models import db


def create_app(name='cheztache'):
    """
    Flask App factory

    :return: flask app
    """
    app = Flask(name)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/db.chez-tache.sqlite'  # noqa
    db.init_app(app)
    return app
