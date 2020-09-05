import os
import pytest

os.environ['FLASK_ENV'] = 'test'
from asobann import deploy


@pytest.fixture
def default_kits_and_components():
    deploy.purge_kits_and_components()