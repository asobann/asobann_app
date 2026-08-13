import random
import json
from pathlib import Path
import datetime

tables = None
table_metas = None


def generate_new_tablename():
    return str(random.randint(0, 9999)) + ''.join([random.choice('abddefghijklmnopqrstuvwxyz') for i in range(3)])


async def get(tablename):
    data = await tables.find_one({"tablename": tablename})
    if not data:
        return None
    return data["table"]


async def create(tablename, prepared_table):
    if prepared_table is None:
        with open(str(Path(__file__).parent / "./default_table.json")) as f:
            table = json.load(f)
    elif prepared_table == '0':
        table = {'components': {}, 'kits': [], 'players': {}}

    await tables.insert_one({"tablename": tablename, "table": table})
    await table_metas.insert_one({"tablename": tablename, "created_at": datetime.datetime.now()})
    return table


async def store(tablename, table):
    table["tablename"] = tablename
    await tables.update_one(
        {"tablename": tablename},
        {"$set": {"table": table}},
        upsert=True)
    await table_metas.update_one(
        {"tablename": tablename},
        {"$set": {"updated_at": datetime.datetime.now()}})


async def purge_all():
    await tables.delete_many({})


async def update_table(tablename, table):
    await tables.update_one({"tablename": tablename}, {"$set": {"table": table}})
    await table_metas.update_one(
        {"tablename": tablename},
        {"$set": {"updated_at": datetime.datetime.now()}})


def connect(mongo_db):
    global tables, table_metas
    tables = mongo_db.tables
    table_metas = mongo_db.table_metas


async def update_components(tablename, diff_of_components, volatile_keys=None):
    current_table = await get(tablename)
    volatile_keys = volatile_keys or {}
    modification = {}
    for diff in diff_of_components:
        for component_id in diff.keys():
            if component_id not in current_table["components"]:
                continue
            skip_keys = volatile_keys.get(component_id, [])
            for key in diff[component_id].keys():
                if key in skip_keys:
                    continue
                mod_key = f'table.components.{component_id}.{key}'
                modification[mod_key] = diff[component_id][key]
    if not modification:
        return
    await tables.update_one({"tablename": tablename}, {"$set": modification})


async def add_new_kit_and_components(tablename, kitData, components):
    await tables.update_one({"tablename": tablename}, {"$push": {"table.kits": kitData}})
    modification = {}
    for component_id in components.keys():
        mod_key = f'table.components.{component_id}'
        modification[mod_key] = components[component_id]
    if not modification:
        # update_one() will fail if $set is empty
        return
    await tables.update_one({"tablename": tablename}, {"$set": modification})


class TableNotFound(Exception):
    pass


def _ensure_matched(result, tablename):
    """卓が見つからなかった書き込みを、黙って捨てずに落とす。

    卓全体を読んでから書き戻していた頃は、読んだ時点で存在しない卓が None として
    返り、その後のアクセスで必ず落ちていた。部分更新はフィルタが一致しなくても
    update_one が成功扱いで返るので、放っておくと「クライアントには配信されたのに
    DBには入っていない」状態を無言で作る（リロードで消える）。
    """
    if result.matched_count == 0:
        raise TableNotFound(tablename)


async def remove_components(tablename, component_ids_to_remove):
    # $unset はコンポーネント単位で消すので、卓を読んで丸ごと書き戻す必要がない。
    # 全体書き戻しだと、その間に届いた他プレイヤーの更新を巻き込んで消していた。
    # 存在しないパスへの $unset はエラーにならないので、事前の存在確認も要らない。
    modification = {f'table.components.{component_id}': '' for component_id in component_ids_to_remove}
    if not modification:
        return
    result = await tables.update_one({"tablename": tablename}, {"$unset": modification})
    _ensure_matched(result, tablename)
    await table_metas.update_one(
        {"tablename": tablename},
        {"$set": {"updated_at": datetime.datetime.now()}})


async def add_component(tablename, component_data):
    # componentIdはクライアントが生成する12桁hex（play_session.jsのgenerateComponentId）
    # なので、ドット記法のパスに入れても壊れない。
    component_id = component_data["componentId"]
    result = await tables.update_one(
        {"tablename": tablename},
        {"$set": {f'table.components.{component_id}': component_data}})
    _ensure_matched(result, tablename)
    await table_metas.update_one(
        {"tablename": tablename},
        {"$set": {"updated_at": datetime.datetime.now()}})
