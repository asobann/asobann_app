from pymongo import operations
from . import kits

components = None


async def get(name):
    data = await components.find_one({"name": name})
    if not data:
        return None
    return data["table"]


async def get_for_kit(kit_name):
    kit = await kits.get(kit_name)
    data = components.find({"component.name": {"$in": kit["kit"]["usedComponentNames"]}})
    return [{"component": d["component"]} async for d in data]


async def get_all():
    data = components.find()
    return [{"component": d["component"]} async for d in data]


def connect(mongo_db):
    global components
    components = mongo_db.components


async def store_default(data):
    assert type(data) == list
    assert all(['component' in d for d in data])
    assert all(['name' in d['component'] for d in data])
    await components.bulk_write(
        [operations.UpdateOne({"component.name": c["component"]["name"]}, {"$set": c}, upsert=True)
         for c in data])


async def purge_all():
    await components.delete_many({})


async def create_or_update(data):
    assert 'component' in data
    assert 'name' in data['component']
    if await components.count_documents({"component.name": data['component']['name']}) > 0:
        await update(data)
    else:
        await create(data)


async def create(data):
    await components.insert_one(data)


async def update(data):
    await components.find_one_and_replace({'component.name': data['component']['name']}, data)
