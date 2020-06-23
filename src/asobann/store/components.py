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
    data = components.find({"component.name": {"$in": kit["usedComponentNames"]}})
    return [{"component": d["component"]} for d in data]


def get_all():
    data = components.find()
    return [{"component": d["component"]} for d in data]


def connect(mongo):
    global components
    components = mongo.db.components


def store_default(data):
    components.bulk_write(
        [operations.UpdateOne({"component.name": c["component"]["name"]}, {"$set": c}, upsert=True)
         for c in data])


def purge_all():
    components.delete_many({})
