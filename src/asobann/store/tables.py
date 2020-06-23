import random
import json
from pathlib import Path
import pymongo.database

tables: pymongo.database.Database = None


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
    return table


def store(tablename, table):
    table["tablename"] = tablename
    tables.update_one(
        {"tablename": tablename},
        {"$set": {"table": table}},
        upsert=True)


def purge_all():
    tables.delete_many({})


def update_table(tablename, table):
    tables.update_one({"tablename": tablename}, {"$set": {"table": table}})


def update_component(tablename, component_id, diff):
    table = get(tablename)
    table["components"][component_id].update(diff)
    tables.update_one({"tablename": tablename}, {"$set": {"table": table}})


def add_component(tablename, component_data):
    print(f"add_component({tablename}, {component_data}")
    table = get(tablename)
    table["components"][component_data["componentId"]] = component_data
    tables.update_one({"tablename": tablename}, {"$set": {"table": table}})


def remove_component(tablename, component_id):
    table = get(tablename)
    del table["components"][component_id]
    tables.update_one({"tablename": tablename}, {"$set": {"table": table}})


def add_kit(tablename, kitData):
    table = get(tablename)
    table["kits"].append(kitData)
    tables.update_one({"tablename": tablename}, {"$set": {"table": table}})


def remove_kit(tablename, kit_id):
    table = get(tablename)
    table["kits"] = [e for e in table["kits"] if e["kitId"] != kit_id]
    tables.update_one({"tablename": tablename}, {"$set": {"table": table}})


def connect(mongo):
    global tables
    tables = mongo.db.tables
