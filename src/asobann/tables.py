import random
import json
from pathlib import Path

tables = None


def generate_new_tablename():
    return str(random.randint(0, 9999)) + ''.join([random.choice('abddefghijklmnopqrstuvwxyz') for i in range(3)])


def get(tablename):
    data = tables.find_one({"tablename": tablename})
    if not data:
        return None
    return data["table"]


def create(tablename):
    with open(str(Path(__file__).parent / "./playing_card.json")) as f:
        table = json.load(f)
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


def update_component(tablename, index, diff):
    table = get(tablename)
    table["components"][index].update(diff)
    tables.update_one({"tablename": tablename}, {"$set": {"table": table}})


def add_component(tablename, data):
    table = get(tablename)
    table["components"].append(data)
    tables.update_one({"tablename": tablename}, {"$set": {"table": table}})


def remove_component(tablename, index):
    table = get(tablename)
    del table["components"][index]
    tables.update_one({"tablename": tablename}, {"$set": {"table": table}})


def connect(mongo):
    global tables
    tables = mongo.db.tables
