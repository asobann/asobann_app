import pytest

from asobann import test_server


@pytest.fixture
def client():
    with test_server.app.test_client() as client:
        yield client


def test_index(client):
    resp = client.get('/')
    assert "302 FOUND" == resp.status
    assert "http://localhost/tables/" in resp.headers["Location"]
