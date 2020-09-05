import random
import json
from pathlib import Path
from pymongo import operations
import pymongo.database
from . import kits

components: pymongo.database.Database = None


def get(name):
    data = components.find_one({"name": name})
    if not data:
        return None
    return data["table"]


def get_for_kit(kit_name):
    kit = kits.get(kit_name)
    data = components.find({"component.name": {"$in": kit["kit"]["usedComponentNames"]}})
    return [{"component": d["component"]} for d in data]


def get_all():
    data = components.find()
    return [{"component": d["component"]} for d in data]


def connect(mongo):
    global components
    components = mongo.db.components


def store_default(data):
    assert type(data) == list
    assert all(['component' in d for d in data])
    assert all(['name' in d['component'] for d in data])
    components.bulk_write(
        [operations.UpdateOne({"component.name": c["component"]["name"]}, {"$set": c}, upsert=True)
         for c in data])


def purge_all():
    components.delete_many({})


def create_or_update(data):
    assert 'component' in data
    assert 'name' in data['component']
    if components.count({"component.name": data['component']['name']}) > 0:
        update(data)
    else:
        create(data)


def create(data):
    components.insert_one(data)


def update(data):
    components.find_one_and_replace({'component.name': data['component']['name']}, data)
