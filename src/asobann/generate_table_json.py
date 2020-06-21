from collections import OrderedDict
import json

ATTRS_IN_ORDER = [
    "name",

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
    "image",
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
    'boxOfComponents',
    'cardistry',
    'stowage',
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

    template = {
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
        "handArea": False,
        "top": "0px",
        "left": "300px",
        "height": "150px",
        "width": "150px",
        "text": "Place cards you don't need now here",
        "text_ja": "使わないカード置き場",
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


def generate_psychological_safety_game():
    components = []

    def add_component(c):
        components.append(in_order(c))

    template = {
        "height": "120px",
        "width": "83px",
        "showImage": True,
        "faceup": False,
        "draggable": True,
        "flippable": True,
        "ownable": True,
        "resizable": False,
    }
    z_index = 100

    offset = 0
    for voice in range(35):
        card = {
            "name": f"PsychologicalSafety V{voice + 1:02}",
            "top": f"{offset}px",
            "left": f"{offset + 380 + 100}px",
            "faceupImage": f"/static/images/psychological_safety_v{voice + 1:02}.jpg",
            "facedownImage": "/static/images/psychological_safety_voice_back.png",
            "zIndex": z_index,
        }
        card.update(template)
        add_component(card)
        z_index -= 1
        offset += 1

    offset = 0
    for situation in range(14):
        card = {
            "name": f"PsychologicalSafety S{situation + 1:02}",
            "top": f"{offset + 220}px",
            "left": f"{offset + 380 + 100}px",
            "faceupImage": f"/static/images/psychological_safety_s{situation + 1:02}.jpg",
            "facedownImage": "/static/images/psychological_safety_situation_back.png",
            "zIndex": z_index,
        }
        card.update(template)
        add_component(card)
        z_index -= 1
        offset += 1

    add_component({
        "name": "PsychologicalSafety Board",
        "top": "0",
        "left": "0",
        "height": "500px",
        "width": "354px",
        "showImage": True,
        "image": "/static/images/psychological_safety_board.png",
        "draggable": True,
        "flippable": False,
        "ownable": False,
        "resizable": True,
        "traylike": True,
        "zIndex": z_index,
    })
    z_index -= 1
    add_component({
        "name": "PsychologicalSafety Box for Voice",
        "handArea": False,
        "top": "0px",
        "left": "380px",
        "height": "200px",
        "width": "350px",
        "color": "yellow",
        "text": "Situation Cards",
        "text_ja": "発言＆オプションカード",
        "showImage": False,
        "draggable": True,
        "flippable": False,
        "resizable": False,
        "rollable": False,
        "ownable": False,
        "traylike": True,
        "boxOfComponents": True,
        "cardistry": ['spread out', 'collect', 'shuffle', 'flip all'],
        "zIndex": z_index,
    })
    z_index -= 1
    add_component({
        "name": "PsychologicalSafety Box for Situation",
        "handArea": False,
        "top": "220px",
        "left": "380",
        "height": "150px",
        "width": "350px",
        "color": "green",
        "text": "Situation Cards",
        "text_ja": "状況カード",
        "showImage": False,
        "draggable": True,
        "flippable": False,
        "resizable": False,
        "rollable": False,
        "ownable": False,
        "traylike": True,
        "boxOfComponents": True,
        "cardistry": ['spread out', 'collect', 'shuffle', 'flip all'],
        "zIndex": z_index,
    })
    z_index -= 1
    add_component({
        "name": "PsychologicalSafety Box for Stones",
        "handArea": False,
        "top": "390px",
        "left": "380px",
        "height": "150px",
        "width": "250px",
        "color": "black",
        "text": "Stones",
        "text_ja": "石の置き場",
        "showImage": False,
        "draggable": True,
        "flippable": False,
        "resizable": False,
        "rollable": False,
        "ownable": False,
        "traylike": True,
        "boxOfComponents": True,
        "cardistry": ['spread out', 'collect', 'flip all'],
        "zIndex": z_index,
    })
    z_index -= 1

    box_and_components = {
        "PsychologicalSafety Box for Situation":
            [c["name"] for c in components if "PsychologicalSafety S" in c["name"]],
        "PsychologicalSafety Box for Voice":
            [c["name"] for c in components if "PsychologicalSafety V" in c["name"]],
        "PsychologicalSafety Box for Stones": [],
    }
    return components, box_and_components


def generate_coin():
    return {
        "name": "Coin - Tetradrachm of Athens",
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


def generate_stones():
    stones = []

    def add_component(c):
        stones.append(in_order(c))

    template = {
        "height": "25px",
        "width": "25px",
        "showImage": True,
        "faceup": False,
        "draggable": True,
        "flippable": False,
        "ownable": True,
        "resizable": False,
    }

    offset = 0
    for stone in range(4):
        s = {
            "name": f"Transparent Stone {stone + 1:02}",
            "top": f"{offset}px",
            "left": f"{offset + 100}px",
            "image": f"/static/images/transparent_stone_{stone + 1:02}.png",
        }
        s.update(template)
        add_component(s)
        offset += 1

    return stones


def write_initial_deploy_data_json():
    output = dict(components=[], kits=[])

    playing_cards = [{"component": c} for c in generate_playing_card()]
    for cmp in playing_cards:
        output["components"].append(cmp)

    dice = {
        "component": {
            "name": "Dice (Blue)",
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

    coin = {"component": generate_coin()}
    output["components"].append(coin)

    psychological_safety_game = generate_psychological_safety_game()
    for cmp in psychological_safety_game[0]:
        output["components"].append({"component": cmp})

    stones = generate_stones()
    for cmp in stones:
        output["components"].append({"component": cmp})

    for kit in [
        {
            "name": "Dice (Blue)",
            "label": "Dice (Blue)",
            "label_ja": "サイコロ（青）",
            "componentNames": [dice["component"]["name"]],
            "width": "64px",
            "height": "64px"
        },
        {
            "name": "Playing Card",
            "label": "Playing Card",
            "label_ja": "トランプ",
            "componentNames": [c["component"]["name"] for c in playing_cards],
            "width": "400px",
            "height": "150px"
        },
        {
            "name": "Coin - Tetradrachm of Athens",
            "label": "Coin",
            "label_ja": "コイン",
            "componentNames": [c["component"]["name"] for c in [coin]],
            "width": "100px",
            "height": "100px"
        },
        {
            "name": "Psychological Safety Game",
            "label": "Psychological Safety Game",
            "label_ja": "心理的安全性ゲーム",
            "componentNames": [c["name"] for c in psychological_safety_game[0]],
            "boxAndComponents": psychological_safety_game[1],
            "width": "1200px",
            "height": "1200px"
        },
        {
            "name": "Transparent Stones",
            "label": "Transparent Stones",
            "label_ja": "宝石(セット)",
            "componentNames": [c["name"] for c in stones],
            "boxAndComponents": {},
            "width": "200px",
            "height": "200px"
        },
    ]:
        output["kits"].append({"kit": kit})

    with open("initial_deploy_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    write_default_table_json()
    write_initial_deploy_data_json()
