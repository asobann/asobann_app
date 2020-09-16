import os
import pytest

os.environ['FLASK_ENV'] = 'test'
from asobann import deploy


@pytest.fixture
def no_kits_and_components():
    deploy.purge_kits_and_components()
    yield
    deploy.load_default()
