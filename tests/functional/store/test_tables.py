import asyncio
import os

import pytest
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

    class TestAddComponent:
        async def test_adds_the_component(self, simple_table):
            await tables.add_component('table1', {'componentId': 'component9', 'name': 'card'})
            read = await tables.get('table1')
            assert read['components']['component9'] == {'componentId': 'component9', 'name': 'card'}

        async def test_leaves_other_components_alone(self, table_with_several_components):
            await tables.add_component('table1', {'componentId': 'component9'})
            read = await tables.get('table1')
            assert read['components']['component1'] == {'value1': 10, 'value2': 20}
            assert len(read['components']) == 4

        async def test_unknown_table_raises(self, no_tables):
            # 部分更新はフィルタが一致しなくても update_one が成功扱いで返るので、
            # 明示的に落とさないと「配信されたのに保存されていない」状態を無言で作る。
            with pytest.raises(tables.TableNotFound):
                await tables.add_component('no_such_table', {'componentId': 'component9'})

    class TestConcurrency:
        """卓全体のread-modify-writeをやめたことで、並行更新が消えなくなったこと。

        複数のFargateタスクはイベントループを共有しないので、「両方が読んでから
        両方が書く」交差は普通に起きる。ここでは asyncio.gather で同じ交差を作る。
        いずれのテストも、全体書き戻し版の実装では落ちる。
        """

        @pytest_asyncio.fixture(autouse=True)
        async def warm_pool(self, app):
            # 接続プールが冷えていると交差が起きない。2本目のコルーチンが新規接続の
            # 確立(TCP+ハンドシェイク)を待つ間に、1本目が読み書きを完走してしまうため。
            # 先に並行read を1回流してコネクションを2本張らせ、以降のgatherが本当に
            # 交差するようにする。これが無いと、旧実装でもテストが通ってしまう。
            await asyncio.gather(tables.get('table1'), tables.get('table1'))

        async def test_concurrent_add_component_keeps_both(self, simple_table):
            await asyncio.gather(
                tables.add_component('table1', {'componentId': 'componentA'}),
                tables.add_component('table1', {'componentId': 'componentB'}),
            )
            read = await tables.get('table1')
            assert 'componentA' in read['components']
            assert 'componentB' in read['components']

        # gather の起動順がそのまま書き込み順になるので、「後から書くほう」を
        # 全体書き戻しにする順序で並べること。逆にすると、全体書き戻しの上に
        # 部分$setが乗って上書きが起きず、旧実装でも通ってしまう（実際に踏んだ）。
        async def test_remove_does_not_clobber_concurrent_update(self, table_with_several_components):
            await asyncio.gather(
                tables.update_components('table1', [{'component2': {'value1': 999}}]),
                tables.remove_components('table1', ['component1']),
            )
            read = await tables.get('table1')
            assert 'component1' not in read['components']
            assert read['components']['component2']['value1'] == 999

        async def test_add_does_not_clobber_concurrent_update(self, table_with_several_components):
            await asyncio.gather(
                tables.update_components('table1', [{'component2': {'value1': 999}}]),
                tables.add_component('table1', {'componentId': 'component9'}),
            )
            read = await tables.get('table1')
            assert 'component9' in read['components']
            assert read['components']['component2']['value1'] == 999

    class TestRemoveComponents:
        async def test_removes_only_the_specified(self, table_with_several_components):
            await tables.remove_components('table1', ['component2'])
            read = await tables.get('table1')
            assert sorted(read['components']) == ['component1', 'component3']

        async def test_unknown_component_id_is_ignored(self, table_with_several_components):
            # $unset は存在しないパスでもエラーにならない。全体読み書き版は
            # del で KeyError になっていた。
            await tables.remove_components('table1', ['no_such_component'])
            read = await tables.get('table1')
            assert len(read['components']) == 3

        async def test_empty_list_writes_nothing(self, table_with_several_components):
            await tables.remove_components('table1', [])
            read = await tables.get('table1')
            assert len(read['components']) == 3

        async def test_unknown_table_raises(self, no_tables):
            with pytest.raises(tables.TableNotFound):
                await tables.remove_components('no_such_table', ['component1'])

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
