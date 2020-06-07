from collections import OrderedDict
import json

ATTRS_IN_ORDER = [
    "name",
    "kitName",

    # display
    "top",
    "left",
    "height",
    "width",
    "color",
    "textColor",
    "showImage",
    "faceupImage",
    "faceupText",
    "facedownImage",
    "facedownText",

    # behavior
    "handArea",
    "draggable",
    "flippable",
    "ownable",
    "resizable",
    "rollable",
    "traylike",
    "onAdd",

    # current status
    "owner",
    "faceup",
    "zIndex",
]


def in_order(component):
    result = OrderedDict()
    keys = set(component.keys())
    for k in ATTRS_IN_ORDER:
        if k not in keys:
            continue
        result[k] = component[k]
        keys.remove(k)
    if len(keys) > 0:
        raise ValueError(f"component contains unknown keys: {keys}")
    return result


# noinspection PyDictCreation
table = {
    "components": {},
    "players": {},
    "tablename": "dummy",
}


table["components"] = {
    "0001": {
        "name": "title",
        "top": "20px",
        "left": "20px",
        "width": "300px",
        "height": "40px",
        "text": "トランプのテーブルへようこそ！",
        "color": "blue",
        "draggable": True,
        "flippable": False,
        "ownable": False,
        "resizable": True,
        "showImage": False,
        "zIndex": 1
    },
    "0002": {
        "name": "usage",
        "top": "20px",
        "left": "340px",
        "height": "200px",
        "width": "400px",
        "color": "darkgoldenrod",
        "showImage": False,
        "faceupText": " - ドラッグで移動\n - ダブルクリックで裏返す\n - テーブルをドラッグしてスクロール\n - URLをシェアすれば招待できる\n - Add Hand Area(左のメニュー)で手札エリアを作る\n - 手札エリアに置いたカードは自分のものになり表にしても見えない\n - まだバグがいっぱいあります！",
        "facedownText": "使い方 (ダブルクリックしてね)",
        "draggable": True,
        "flippable": True,
        "ownable": False,
        "resizable": True,
        "zIndex": 2
    },
}

count = 3
z_index = 100
offset = 0
for suit, prefix, color in [("♠", "S", "black"), ("♥", "H", "red"), ("♦", "D", "red"), ("♣", "C", "black")]:
    for rank in ["A", "K", "Q", "J", "10", "9", "8", "7", "6", "5", "4", "3", "2"]:
        table["components"][f"C{count:04}"] = {
            "name": f"PlayingCard {prefix}_{rank}",
            "kitName": "Playing Card",
            "top": f"{offset}px",
            "left": f"{offset}px",
            "height": "100px",
            "width": "75px",
            "textColor": color,
            "showImage": True,
            "faceupImage": "/static/images/playing_card_up.png",
            "faceupText": f"{suit}{rank}",
            "facedownImage": "/static/images/playing_card_back.png",
            "facedownText": "",
            "faceup": False,
            "draggable": True,
            "flippable": True,
            "ownable": True,
            "resizable": False,
            "zIndex": z_index
        }
        count += 1
        z_index -= 1
        offset += 1

for i in range(2):
    table["components"][f"C{count:04}"] = {
        "name": f"JOKER{i + 1}",
        "top": f"{offset}px",
        "left": f"{offset}px",
        "height": "100px",
        "width": "75px",
        "textColor": "black",
        "showImage": True,
        "faceupImage": "/static/images/playing_card_up.png",
        "faceupText": "JOKER",
        "facedownImage": "/static/images/playing_card_back.png",
        "facedownText": "",
        "faceup": False,
        "draggable": True,
        "flippable": True,
        "ownable": True,
        "resizable": False,
        "zIndex": z_index
    }
    count += 1
    z_index -= 1
    offset += 1


print(json.dumps(table, indent=2))