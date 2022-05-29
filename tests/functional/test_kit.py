import os
import pytest
import json

os.environ["FLASK_ENV"] = "test"

# pylint: disable=E402
from asobann import wsgi

pytestmark = [pytest.mark.quick]


@pytest.fixture
def app():
    return wsgi.app


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client


def test_get_kits(client):
    resp = client.get('/kits')
    data = json.loads(resp.data)
    assert len(data) > 0
    assert data[0]['kit']['name'] == 'Note'

