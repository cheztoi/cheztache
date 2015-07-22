
import os
import tempfile


class DefaultConfig(object):
    DEBUG = False
    TESTING = False
    ROOT_DIRECTORY = os.path.expanduser('~/.chez')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///{}'.format(os.path.join(
        ROOT_DIRECTORY, 'db.tache.sqlite'))


class DevelopmentConfig(DefaultConfig):
    DEBUG = True
    ROOT_DIRECTORY = '/tmp/chez'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///{}'.format(os.path.join(
        ROOT_DIRECTORY, 'db.tache.sqlite'))


class TestingConfig(DefaultConfig):
    TESTING = True
    ROOT_DIRECTORY = tempfile.mkdtemp()
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
