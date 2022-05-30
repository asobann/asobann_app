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


@pytest.fixture
def table_with_several_components():
    table = {
        'components': {
            'component1': {'value1': 10, 'value2': 20},
            'component2': {'value1': 110, 'value2': 120},
            'component3': {'value1': 210, 'value2': 220},
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

    class TestUpdateComponents:
        def test_update_components_basic(self, simple_table):
            tables.update_components('table1', [{'component1': {'value1': 100}}])
            assert tables.get('table1')['components']['component1'] == {'value1': 100, 'value2': 20}

        def test_update_components_only_specified_value(self, simple_table):
            tables.store('table1', {
                'components': {
                    'component1': {'value1': 100, 'value2': 200},
                },
                'kits': [],
                'players': {},
            })
            tables.update_components('table1', [{'component1': {'value1': 11}}])
            assert tables.get('table1')['components']['component1'] == {'value1': 11, 'value2': 200}

        def test_update_components_several_components(self, table_with_several_components):
            tables.update_components('table1',
                                     [
                                         {'component1': {'value1': 300}},
                                         {'component2': {'value1': 300}},
                                         {'component3': {'value1': 300}},
                                     ])
            assert tables.get('table1')['components']['component1'] == {'value1': 300, 'value2': 20}
            assert tables.get('table1')['components']['component2'] == {'value1': 300, 'value2': 120}
            assert tables.get('table1')['components']['component3'] == {'value1': 300, 'value2': 220}

    class TestAddNewKitAndComponents:
        def test_usual(self, simple_table):
            tables.add_new_kit_and_components(
                tablename='table1',
                kitData={'name': 'kit1', 'kitId': 'kit001'},
                components={'component9': {'value1': 10, 'value2': 20}, })
            assert 'kit001' in [k['kitId'] for k in tables.get('table1')['kits']]
            assert 'component9' in tables.get('table1')['components']
            assert tables.get('table1')['components']['component9'] == {'value1': 10, 'value2': 20}

        def test_components_is_empty(self, simple_table):
            tables.add_new_kit_and_components(
                tablename='table1',
                kitData={'name': 'kit1', 'kitId': 'kit001'},
                components={})
            assert len(tables.get('table1')['components']) == len(simple_table['components'])
