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
    "text_ja",
    "faceupImage",
    "faceupText",
    "faceupText_ja",
    "facedownImage",
    "facedownText",
    "facedownText_ja",

    # behavior
    "handArea",
    "draggable",
    "flippable",
    "ownable",
    "resizable",
    "rollable",
    "traylike",
    "onAdd",
    'boxOfComponents',
    'cardistry',
    'stowage',

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
                "left": f"{offset + 100}px",
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
            "left": f"{offset + 100}px",
            "textColor": "black",
            "faceupText": "JOKER",
            "zIndex": z_index,
        }
        card.update(template)
        add_component(card)
        z_index -= 1
        offset += 1

    add_component({
        "name": "Playing Card Box",
        "kitName": "Playing Card",
        "handArea": False,
        "top": "0px",
        "left": "0px",
        "height": "200px",
        "width": "250px",
        "color": "blue",
        "showImage": False,
        "draggable": True,
        "flippable": False,
        "resizable": False,
        "rollable": False,
        "ownable": False,
        "traylike": True,
        "boxOfComponents": True,
        "cardistry": ["spread out", "collect", "shuffle", 'flip all'],
        "zIndex": 1,
    })
    add_component({
        "name": "Stowage for Unused Cards",
        "kitName": "Playing Card",
        "handArea": False,
        "top": "0px",
        "left": "300px",
        "height": "150px",
        "width": "150px",
        "text": "Place cards you don't need now in here",
        "text_ja": "不要なカード置き場",
        "color": "darkgrey",
        "showImage": False,
        "draggable": True,
        "flippable": False,
        "resizable": True,
        "rollable": False,
        "ownable": False,
        "traylike": True,
        "stowage": True,
        "boxOfComponents": False,
        "zIndex": 1,
    })
    return playing_card


def generate_coin():
    return {
        "name": "Coin - Tetradrachm of Athens",
        "kitName": "Coin - Tetradrachm of Athens",
        "top": "0px",
        "left": "0px",
        "height": "80px",
        "width": "80px",
        "faceupImage": "/static/images/coin_TetradrachmOfAthens_head.png",
        "facedownImage": "/static/images/coin_TetradrachmOfAthens_tail.png",
        "showImage": True,
        "draggable": True,
        "flippable": True,
        "ownable": False,
        "resizable": True,
    }


def write_default_table_json():
    table = OrderedDict(
        components=OrderedDict(),
        kits=[],
        players=OrderedDict(),
        tablename="dummy"
    )

    table["components"]["title"] = {
        "name": "title",
        "top": "20px",
        "left": "20px",
        "width": "300px",
        "height": "40px",
        "text": "Welcome to a new table!",
        "text_ja": "新しいテーブルへようこそ！",
        "color": "blue",
        "draggable": True,
        "flippable": False,
        "ownable": False,
        "resizable": True,
        "showImage": False,
        "zIndex": 1,
    }

    table["components"]["usage"] = {
        "name": "usage",
        "top": "20px",
        "left": "340px",
        "height": "250px",
        "width": "400px",
        "color": "darkgoldenrod",
        "showImage": False,
        "faceupText": "- Use Add / Remove Kits (to the left) have components on the table\n - Drag to move\n - Double click to flip\n - Drag the table to scroll\n - Share URL to invite people\n - Add Hand Area (to the left) to have your own cards (hand)\n - Cards in your hand won't be seen by others\n - Enjoy! but you might encounter some issues... Please let us know when you see one",
        "faceupText_ja": " - 左の「テーブルに出す」からトランプなどを取り出す\n - ドラッグで移動\n - ダブルクリックで裏返す\n - テーブルをドラッグしてスクロール\n - URLをシェアすれば招待できる\n - 左の「手札エリアを作る」で自分の手札エリアを作る\n - 手札エリアに置いたカードは自分のものになり 表にしても見えない\n - まだ不具合や未実装の部分があります。気になる点はお知らせください",
        "facedownText": "How to use (double click to read)",
        "facedownText_ja": "使い方 (ダブルクリックしてね)",
        "draggable": True,
        "flippable": True,
        "ownable": False,
        "resizable": True,
        "zIndex": 2,
    }

    with open("store/default_table.json", "w", encoding="utf-8") as f:
        json.dump(table, f, indent=2)


def write_initial_deploy_data_json():
    output = dict(components=[], kits=[])

    for cmp in generate_playing_card():
        output["components"].append({"component": cmp})

    dice = {
        "component": {
            "name": "Dice (Blue)",
            "kitName": "Dice (Blue)",
            "handArea": False,
            "top": "0px",
            "left": "0px",
            "height": "64px",
            "width": "64px",
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
    output["components"].append({"component": generate_coin()})

    for kit in [
        {
            "name": "Dice (Blue)",
            "label":  "Dice (Blue)",
            "label_ja":  "サイコロ（青）",
            "width": "64px",
            "height": "64px"
        },
        {
            "name": "Playing Card",
            "label":  "Playing Card",
            "label_ja":  "トランプ",
            "width": "400px",
            "height": "150px"
        },
        {
            "name": "Coin - Tetradrachm of Athens",
            "label":  "Coin",
            "label_ja":  "コイン",
            "width": "100px",
            "height": "100px"

        }
    ]:
        output["kits"].append({"kit": kit})

    with open("initial_deploy_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    write_default_table_json()
    write_initial_deploy_data_json()
