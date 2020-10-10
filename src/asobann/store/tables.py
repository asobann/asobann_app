from flask import current_app
import random
import json
from pathlib import Path
import pymongo.database
import datetime

tables: pymongo.database.Database = None
table_metas: pymongo.database.Database = None


def generate_new_tablename():
    return str(random.randint(0, 9999)) + ''.join([random.choice('abddefghijklmnopqrstuvwxyz') for i in range(3)])


def get(tablename):
    data = tables.find_one({"tablename": tablename})
    if not data:
        return None
    return data["table"]


def create(tablename, prepared_table):
    if prepared_table is None:
        with open(str(Path(__file__).parent / "./default_table.json")) as f:
            table = json.load(f)
    elif prepared_table == '0':
        table = {'components': {}, 'kits': [], 'players': {}}

    tables.insert_one({"tablename": tablename, "table": table})
    table_metas.insert_one({"tablename": tablename, "created_at": datetime.datetime.now()})
    return table


def store(tablename, table):
    table["tablename"] = tablename
    tables.update_one(
        {"tablename": tablename},
        {"$set": {"table": table}},
        upsert=True)
    table_metas.update_one(
        {"tablename": tablename},
        {"$set": {"updated_at": datetime.datetime.now()}})


def purge_all():
    tables.delete_many({})


def update_table(tablename, table):
    tables.update_one({"tablename": tablename}, {"$set": {"table": table}})
    table_metas.update_one(
        {"tablename": tablename},
        {"$set": {"updated_at": datetime.datetime.now()}})


def add_component(tablename, component_data):
    print(f"add_component({tablename}, {component_data}")
    table = get(tablename)
    table["components"][component_data["componentId"]] = component_data
    tables.update_one({"tablename": tablename}, {"$set": {"table": table}})
    table_metas.update_one(
        {"tablename": tablename},
        {"$set": {"updated_at": datetime.datetime.now()}})


def remove_component(tablename, component_id):
    table = get(tablename)
    del table["components"][component_id]
    tables.update_one({"tablename": tablename}, {"$set": {"table": table}})
    table_metas.update_one(
        {"tablename": tablename},
        {"$set": {"updated_at": datetime.datetime.now()}})


def add_kit(tablename, kitData):
    table = get(tablename)
    table["kits"].append(kitData)
    tables.update_one({"tablename": tablename}, {"$set": {"table": table}})
    table_metas.update_one(
        {"tablename": tablename},
        {"$set": {"updated_at": datetime.datetime.now()}})


def remove_kit(tablename, kit_id):
    table = get(tablename)
    table["kits"] = [e for e in table["kits"] if e["kitId"] != kit_id]
    tables.update_one({"tablename": tablename}, {"$set": {"table": table}})
    table_metas.update_one(
        {"tablename": tablename},
        {"$set": {"updated_at": datetime.datetime.now()}})


def connect(mongo):
    global tables, table_metas
    tables = mongo.db.tables
    table_metas = mongo.db.table_metas


def update_components(tablename, diff_of_components):
    current_table = get(tablename)
    modification = {}
    i = 0
    for diff in diff_of_components:
        for component_id in diff.keys():
            if component_id not in current_table["components"]:
                continue
            i += 1
            for key in diff[component_id].keys():
                mod_key = f'table.components.{component_id}.{key}'
                # current_app.logger.info(f'  {i:3} {mod_key}={diff[component_id][key]}')
                modification[mod_key] = diff[component_id][key]
    if not modification:
        return
    tables.update_one({"tablename": tablename}, {"$set": modification})


def add_new_kit_and_components(tablename, kit, components):
    tables.update_one({"tablename": tablename}, {"$push": {"table.kits": kit}})
    modification = {}
    for component_id in components.keys():
        mod_key = f'table.components.{component_id}'
        modification[mod_key] = components[component_id]
    tables.update_one({"tablename": tablename}, {"$set": modification})
