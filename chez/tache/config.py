
import os


class DefaultConfig(object):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = (
        'sqlite:///{}'.format(os.path.expanduser('~/.chez/db.tache.sqlite')))


class DevelopmentConfig(DefaultConfig):
    DEBUG = True


class TestingConfig(DefaultConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
