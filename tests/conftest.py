
import pytest
from chez.tache.factory import create_app


@pytest.fixture
def app():
    app = create_app(config='chez.tache.config.TestingConfig')
    return app
