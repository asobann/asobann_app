import os
import pytest

os.environ["FLASK_ENV"] = "test"

from asobann import wsgi
from asobann.store import tables

pytestmark = [pytest.mark.quick]


@pytest.fixture
def app():
    return wsgi.app


def test_create_new_table(app):
    tables.create('table1', '0')
    table = tables.get('table1')
    assert table
    assert table['components'] == {}
    assert table['kits'] == []
    assert table['players'] == {}
