import os
import pytest

os.environ["FLASK_ENV"] = "test"

from asobann import wsgi


@pytest.fixture
def client():
    with wsgi.app.test_client() as client:
        yield client


def test_index(client):
    resp = client.get('/')
    assert "302 FOUND" == resp.status
    assert "http://localhost/tables/" in resp.headers["Location"]
