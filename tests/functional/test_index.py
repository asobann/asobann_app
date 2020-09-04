import os
import pytest

os.environ["FLASK_ENV"] = "test"

from asobann import wsgi

pytestmark = [pytest.mark.quick]


@pytest.fixture
def app():
    return wsgi.app


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client


def test_index(client):
    resp = client.get('/')
    assert "302 FOUND" == resp.status
    assert "http://localhost/tables/" in resp.headers["Location"]


def test_googleanalytics_unavailable_in_dev(client):
    resp = client.get('/tables/0123abc')
    assert b'Google Analytics' not in resp.data


def test_googleanalytics_available_in_prod(app, client):
    app.config['GOOGLE_ANALYTICS_ID'] = 'dummy-id'
    resp = client.get('/tables/0123abc')
    assert b'Google Analytics' in resp.data
    assert b'UA-' not in resp.data
    assert b'id=dummy-id' in resp.data
