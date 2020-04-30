import random

tables = None


def generate_new_tablename():
    return str(random.randint(0, 9999)) + ''.join([random.choice('abddefghijklmnopqrstuvwxyz') for i in range(3)])


def get(tablename):
    data = tables.find_one({"tablename": tablename})
    if not data:
        return None
    return data["table"]


def create(tablename):
    table = {
        "tablename": tablename,
        "components": [
            {
                "name": "title",
                "text": "Welcome to Playing Card Table!",
                "top": "20px",
                "left": "20px",
                "width": "300px",
                "height": "40px",
                "color": "blue",
                "draggable": True,
                "flippable": False,
                "resizable": True,
                "ownable": False,
                "showImage": False,
                "zIndex": 1,
            },
            {
                "name": "usage",
                "top": "20px",
                "left": "340px",
                "width": "400px",
                "height": "200px",
                "color": "darkgoldenrod",
                "draggable": True,
                "flippable": True,
                "facedownText": "usage (double click to open)",
                "faceupText": " - drag to move.\n"
                              " - double click to flip.\n"
                              " - drag table to scroll around.\n"
                              " - invite people with URL.\n"
                              " - add hand area (in the menu).\n"
                              " - place cards in your hand area to own.\n",
                "resizable": True,
                "ownable": False,
                "showImage": False,
                "zIndex": 1,
            },
            {
                "name": "S01",
                "top": "300px",
                "left": "400px",
                "width": "75px",
                "height": "100px",
                "draggable": True,
                "flippable": True,
                "resizable": False,
                "ownable": True,
                "faceup": False,
                "showImage": True,
                "textColor": "black",
                "faceupText" : "♠A",
                "facedownText" : "Playing Card",
                "faceupImage": "/static/images/v01.jpg",
                "facedownImage": "/static/images/voice_back.png",
                "zIndex": 55,
            },
            {
                "name": "S02",
                "top": "301px",
                "left": "401px",
                "width": "75px",
                "height": "100px",
                "draggable": True,
                "flippable": True,
                "resizable": False,
                "ownable": True,
                "faceup": False,
                "showImage": True,
                "textColor": "black",
                "faceupText" : "♠2",
                "facedownText" : "Playing Card",
                "faceupImage": "/static/images/v01.jpg",
                "facedownImage": "/static/images/voice_back.png",
                "zIndex": 54,
            },
            {
                "name": "S03",
                "top": "302px",
                "left": "402px",
                "width": "75px",
                "height": "100px",
                "draggable": True,
                "flippable": True,
                "resizable": False,
                "ownable": True,
                "faceup": False,
                "showImage": True,
                "textColor": "black",
                "faceupText" : "♠3",
                "facedownText" : "Playing Card",
                "faceupImage": "/static/images/v01.jpg",
                "facedownImage": "/static/images/voice_back.png",
                "zIndex": 53,
            },
            {
                "name": "S04",
                "top": "303px",
                "left": "403px",
                "width": "75px",
                "height": "100px",
                "draggable": True,
                "flippable": True,
                "resizable": False,
                "ownable": True,
                "faceup": False,
                "showImage": True,
                "textColor": "black",
                "faceupText" : "♠4",
                "facedownText" : "Playing Card",
                "faceupImage": "/static/images/v01.jpg",
                "facedownImage": "/static/images/voice_back.png",
                "zIndex": 52,
            },
            {
                "name": "S05",
                "top": "304px",
                "left": "404px",
                "width": "75px",
                "height": "100px",
                "draggable": True,
                "flippable": True,
                "resizable": False,
                "ownable": True,
                "faceup": False,
                "showImage": True,
                "textColor": "black",
                "faceupText" : "♠5",
                "facedownText" : "Playing Card",
                "faceupImage": "/static/images/v01.jpg",
                "facedownImage": "/static/images/voice_back.png",
                "zIndex": 51,
            },
            {
                "name": "S06",
                "top": "305px",
                "left": "405px",
                "width": "75px",
                "height": "100px",
                "draggable": True,
                "flippable": True,
                "resizable": False,
                "ownable": True,
                "faceup": False,
                "showImage": True,
                "textColor": "black",
                "faceupText" : "♠6",
                "facedownText" : "Playing Card",
                "faceupImage": "/static/images/v01.jpg",
                "facedownImage": "/static/images/voice_back.png",
                "zIndex": 50,
            },
            {
                "name": "H01",
                "top": "306px",
                "left": "406px",
                "width": "75px",
                "height": "100px",
                "draggable": True,
                "flippable": True,
                "resizable": False,
                "ownable": True,
                "faceup": False,
                "showImage": True,
                "textColor": "red",
                "faceupText" : "♥A",
                "facedownText" : "Playing Card",
                "faceupImage": "/static/images/v01.jpg",
                "facedownImage": "/static/images/voice_back.png",
                "zIndex": 42,
            },
            {
                "name": "D01",
                "top": "307px",
                "left": "407px",
                "width": "75px",
                "height": "100px",
                "draggable": True,
                "flippable": True,
                "resizable": False,
                "ownable": True,
                "faceup": False,
                "showImage": True,
                "textColor": "red",
                "faceupText" : "♦A",
                "facedownText" : "Playing Card",
                "faceupImage": "/static/images/v01.jpg",
                "facedownImage": "/static/images/voice_back.png",
                "zIndex": 29,
            },
            {
                "name": "C01",
                "top": "308px",
                "left": "408px",
                "width": "75px",
                "height": "100px",
                "draggable": True,
                "flippable": True,
                "resizable": False,
                "ownable": True,
                "faceup": False,
                "showImage": True,
                "textColor": "black",
                "faceupText" : "♣A",
                "facedownText" : "Playing Card",
                "faceupImage": "/static/images/v01.jpg",
                "facedownImage": "/static/images/voice_back.png",
                "zIndex": 16,
            },
        ],
        "players": {},
    }
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
