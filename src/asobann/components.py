import random
import json
from pathlib import Path
from pymongo import operations

components = None


def get(name):
    data = components.find_one({"name": name})
    if not data:
        return None
    return data["table"]


def get_for_kit(kit_name):
    data = components.find({"component.kitName": kit_name})
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
