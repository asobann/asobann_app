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


async def update_components(tablename, diff_of_components):
    current_table = await get(tablename)
    modification = {}
    i = 0
    for diff in diff_of_components:
        for component_id in diff.keys():
            if component_id not in current_table["components"]:
                continue
            i += 1
            for key in diff[component_id].keys():
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


async def remove_components(tablename, component_ids_to_remove):
    table = await get(tablename)
    for component_id in component_ids_to_remove:
        del table["components"][component_id]
    await tables.update_one({"tablename": tablename}, {"$set": {"table": table}})
    await table_metas.update_one(
        {"tablename": tablename},
        {"$set": {"updated_at": datetime.datetime.now()}})
