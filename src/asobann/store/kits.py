from pymongo import operations

kits = None


async def get(name):
    data = await kits.find_one({"kit.name": name})
    if not data:
        return None
    del data['_id']
    return data


async def get_all():
    data = kits.find()
    return [{"kit": d["kit"]} async for d in data]


def connect(mongo_db):
    global kits
    kits = mongo_db.kits


async def create_or_update(kit_data):
    assert 'kit' in kit_data
    assert 'name' in kit_data['kit']
    if await kits.count_documents({"kit.name": kit_data['kit']['name']}) > 0:
        await update(kit_data)
    else:
        await create(kit_data)


async def create(kit_data):
    await kits.insert_one({'kit': kit_data["kit"], 'version': 1})


async def update(kit_data):
    current = await kits.find_one({'kit.name': kit_data['kit']['name']})
    current_version = current['version']
    await kits.find_one_and_replace({'kit.name': kit_data['kit']['name']},
                                     {'kit': kit_data["kit"], 'version': current_version + 1})


async def store_default(data):
    assert type(data) == list
    assert all(['kit' in d for d in data])
    assert all(['name' in d['kit'] for d in data])
    await kits.bulk_write(
        [operations.UpdateOne({"kit.name": c["kit"]["name"]}, {"$set": c}, upsert=True) for c in data])


async def purge_all():
    await kits.delete_many({})
