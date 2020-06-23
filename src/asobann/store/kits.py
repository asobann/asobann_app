import random
import json
from pathlib import Path
from pymongo import operations
import pymongo.database

kits: pymongo.database.Database = None


def get(name):
    data = kits.find_one({"kit.name": name})
    if not data:
        return None
    return data["kit"]


def get_all():
    data = kits.find()
    return [{"kit": d["kit"]} for d in data]


def connect(mongo):
    global kits
    kits = mongo.db.kits


def store_default(data):
    kits.bulk_write(
        [operations.UpdateOne({"kit.name": c["kit"]["name"]}, {"$set": c}, upsert=True) for c in data])


def purge_all():
    kits.delete_many({})
