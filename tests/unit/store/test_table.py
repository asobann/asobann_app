import os
import pytest

os.environ["FLASK_ENV"] = "test"

from asobann import wsgi
from asobann.store import tables

pytestmark = [pytest.mark.quick]


@pytest.fixture
def app():
    return wsgi.app


@pytest.fixture
def no_tables():
    tables.tables.delete_many({})


@pytest.fixture
def simple_table():
    table = {
        'components': {
            'component1': {'value1': 10, 'value2': 20},
        },
        'kits': [],
        'players': {},
    }
    tables.store('table1', table)
    return table


@pytest.mark.usefixtures('app', 'no_tables')
class TestTableStore:
    def test_create_new_table(self):
        tables.create('table1', '0')
        table = tables.get('table1')
        assert table
        assert table['components'] == {}
        assert table['kits'] == []
        assert table['players'] == {}

    def test_store_to_create_new(self):
        table = {
            'components': {
                'component1': {'value1': 10, 'value2': 20},
            },
            'kits': [],
            'players': {},
        }
        tables.store('table1', table)

        read = tables.get('table1')
        assert read['components']['component1'] == {'value1': 10, 'value2': 20}

    def test_update(self, simple_table):
        simple_table['components']['component1']['value1'] = 100
        tables.update_table('table1', simple_table)

        assert tables.get('table1')['components']['component1'] == {'value1': 100, 'value2': 20}
