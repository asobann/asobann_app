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
    "text",
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


def generate_playing_card():
    playing_card = []

    def add_component(c):
        playing_card.append(in_order(c))

    add_component({
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
        "zIndex": 1,
    })
    add_component({
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
        "zIndex": 2,
    })

    template = {
        "kitName": "Playing Card",
        "height": "100px",
        "width": "75px",
        "showImage": True,
        "faceupImage": "/static/images/playing_card_up.png",
        "facedownImage": "/static/images/playing_card_back.png",
        "facedownText": "",
        "faceup": False,
        "draggable": True,
        "flippable": True,
        "ownable": True,
        "resizable": False,
    }
    z_index = 100
    offset = 0
    for suit, prefix, color in [("♠", "S", "black"), ("♥", "H", "red"), ("♦", "D", "red"), ("♣", "C", "black")]:
        for rank in ["A", "K", "Q", "J", "10", "9", "8", "7", "6", "5", "4", "3", "2"]:
            card = {
                "name": f"PlayingCard {prefix}_{rank}",
                "top": f"{offset}px",
                "left": f"{offset}px",
                "textColor": color,
                "faceupText": f"{suit}{rank}",
                "zIndex": z_index,
            }
            card.update(template)
            add_component(card)
            z_index -= 1
            offset += 1

    for i in range(2):
        card = {
            "name": f"JOKER{i + 1}",
            "top": f"{offset}px",
            "left": f"{offset}px",
            "textColor": "black",
            "faceupText": "JOKER",
            "zIndex": z_index,
        }
        card.update(template)
        add_component(card)
        z_index -= 1
        offset += 1

    return playing_card


def write_default_table_json():
    table = OrderedDict(
        components=OrderedDict(),
        players=OrderedDict(),
        tablename="dummy"
    )

    for i, cmp in enumerate(generate_playing_card()):
        table["components"][f"C{i:04}"] = cmp

    with open("default_table.json", "w", encoding="utf-8") as f:
        json.dump(table, f, indent=2)


def write_initial_deploy_data_json():
    output = dict(components=[], kits=[])
    for cmp in generate_playing_card():
        if "usage" in cmp["name"] or "title" in cmp["name"]:
            continue
        output["components"].append({"component": cmp})

    dice = {
        "component": {
            "name": "Dice (Blue)",
            "kitName": "Dice (Blue)",
            "handArea": False,
            "top": "0px",
            "left": "0px",
            "height": "64px",
            "showImage": False,
            "draggable": True,
            "flippable": False,
            "resizable": False,
            "rollable": True,
            "ownable": False,
            "onAdd": "function(component) { \n"
                     "  component.rollFinalValue = Math.floor(Math.random() * 6) + 1;\n"
                     "  component.rollDuration = 500;\n"
                     "  component.startRoll = true;\n"
                     "}"
        }
    }
    output["components"].append(dice)

    for kit in [
        {
            "name": "Dice (Blue)",
            "width": "64px",
            "height": "64px"
        },
        {
            "name": "Playing Card",
            "width": "150px",
            "height": "150px"
        }
    ]:
        output["kits"].append({"kit": kit})

    with open("initial_deploy_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)


if __name__=="__main__":
    write_default_table_json()
    write_initial_deploy_data_json()
