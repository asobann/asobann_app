import os
import pytest_asyncio

os.environ["FLASK_ENV"] = "test"

import asobann.app
from asobann.store import tables


@pytest_asyncio.fixture
async def app():
    # モジュールトップレベルではなくfixture内で設定する: create_app()はテスト実行時に
    # 呼ばれるため、他のテストファイルが実行順序次第でFLASK_ENVを書き換えている可能性がある。
    os.environ["FLASK_ENV"] = "test"
    return await asobann.app.create_app()


@pytest_asyncio.fixture
async def no_tables(app):
    await tables.tables.delete_many({})


@pytest_asyncio.fixture
async def simple_table(no_tables):
    table = {
        'components': {
            'component1': {'value1': 10, 'value2': 20},
        },
        'kits': [],
        'players': {},
    }
    await tables.store('table1', table)
    return table


@pytest_asyncio.fixture
async def table_with_several_components(no_tables):
    table = {
        'components': {
            'component1': {'value1': 10, 'value2': 20},
            'component2': {'value1': 110, 'value2': 120},
            'component3': {'value1': 210, 'value2': 220},
        },
        'kits': [],
        'players': {},
    }
    await tables.store('table1', table)
    return table


class TestTableStore:
    async def test_create_new_table(self, no_tables):
        await tables.create('table1', '0')
        table = await tables.get('table1')
        assert table
        assert table['components'] == {}
        assert table['kits'] == []
        assert table['players'] == {}

    async def test_store_to_create_new(self, no_tables):
        table = {
            'components': {
                'component1': {'value1': 10, 'value2': 20},
            },
            'kits': [],
            'players': {},
        }
        await tables.store('table1', table)

        read = await tables.get('table1')
        assert read['components']['component1'] == {'value1': 10, 'value2': 20}

    async def test_update(self, simple_table):
        simple_table['components']['component1']['value1'] = 100
        await tables.update_table('table1', simple_table)

        read = await tables.get('table1')
        assert read['components']['component1'] == {'value1': 100, 'value2': 20}

    class TestUpdateComponents:
        async def test_update_components_basic(self, simple_table):
            await tables.update_components('table1', [{'component1': {'value1': 100}}])
            read = await tables.get('table1')
            assert read['components']['component1'] == {'value1': 100, 'value2': 20}

        async def test_update_components_only_specified_value(self, simple_table):
            await tables.store('table1', {
                'components': {
                    'component1': {'value1': 100, 'value2': 200},
                },
                'kits': [],
                'players': {},
            })
            await tables.update_components('table1', [{'component1': {'value1': 11}}])
            read = await tables.get('table1')
            assert read['components']['component1'] == {'value1': 11, 'value2': 200}

        async def test_update_components_several_components(self, table_with_several_components):
            await tables.update_components('table1',
                                            [
                                                {'component1': {'value1': 300}},
                                                {'component2': {'value1': 300}},
                                                {'component3': {'value1': 300}},
                                            ])
            read = await tables.get('table1')
            assert read['components']['component1'] == {'value1': 300, 'value2': 20}
            assert read['components']['component2'] == {'value1': 300, 'value2': 120}
            assert read['components']['component3'] == {'value1': 300, 'value2': 220}

        async def test_update_components_skips_volatile_keys(self, simple_table):
            await tables.update_components(
                'table1',
                [{'component1': {'value1': 999, 'value2': 999}}],
                volatile_keys={'component1': ['value1']})
            read = await tables.get('table1')
            assert read['components']['component1'] == {'value1': 10, 'value2': 999}

        async def test_update_components_all_keys_volatile_writes_nothing(self, simple_table):
            await tables.update_components(
                'table1',
                [{'component1': {'value1': 999, 'value2': 999}}],
                volatile_keys={'component1': ['value1', 'value2']})
            read = await tables.get('table1')
            assert read['components']['component1'] == {'value1': 10, 'value2': 20}

        async def test_update_components_volatile_keys_for_other_component_is_ignored(
                self, table_with_several_components):
            await tables.update_components(
                'table1',
                [
                    {'component1': {'value1': 300}},
                    {'component2': {'value1': 300}},
                ],
                volatile_keys={'component2': ['value1']})
            read = await tables.get('table1')
            assert read['components']['component1'] == {'value1': 300, 'value2': 20}
            assert read['components']['component2'] == {'value1': 110, 'value2': 120}

    class TestAddNewKitAndComponents:
        async def test_usual(self, simple_table):
            await tables.add_new_kit_and_components(
                tablename='table1',
                kitData={'name': 'kit1', 'kitId': 'kit001'},
                components={'component9': {'value1': 10, 'value2': 20}, })
            read = await tables.get('table1')
            assert 'kit001' in [k['kitId'] for k in read['kits']]
            assert 'component9' in read['components']
            assert read['components']['component9'] == {'value1': 10, 'value2': 20}

        async def test_components_is_empty(self, simple_table):
            await tables.add_new_kit_and_components(
                tablename='table1',
                kitData={'name': 'kit1', 'kitId': 'kit001'},
                components={})
            read = await tables.get('table1')
            assert len(read['components']) == len(simple_table['components'])
