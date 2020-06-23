from typing import List, Dict
import math
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
    "textAlign",
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
    'positionOfBoxContents',
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


class Box:
    def __init__(self, kit: 'Kit', box_component: Dict = None):
        self.kit: 'Kit' = kit
        self.box_component: Dict = box_component
        self.content_names: List[str] = []

    def add_component(self, data, template=None):
        self.kit.registry.add_component(data, template=template)
        self.content_names.append(data['name'])

    @property
    def box_component(self):
        return self._box_component

    @box_component.setter
    def box_component(self, box_component):
        self._box_component = box_component
        if box_component:
            self.kit.registry.add_component(box_component)

    def use_components(self, components):
        for c in components:
            if type(c) == str:
                self.content_names.append(c)
            else:
                raise ValueError()


class Kit:
    def __init__(self, registry: 'ComponentRegistry'):
        self.registry: 'ComponentRegistry' = registry
        self._description: Dict = {}
        self.direct_component_names: List[str] = []
        self.boxes: List[Box] = []

    def box(self, box_component=None) -> Box:
        box = Box(self, box_component)
        self.boxes.append(box)
        return box

    def add_component(self, data, template=None):
        self.registry.add_component(data, template=template)
        self.direct_component_names.append(data['name'])

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value


class ComponentRegistry:
    def __init__(self):
        self.components: List = []
        self.kits: List[Kit] = []

    def add_component(self, data, template=None):
        if template:
            completeData = template.copy()
            completeData.update(data)
        else:
            completeData = data.copy()
        for c in self.components:
            if c['name'] == completeData['name']:
                assert c == completeData
                break
        else:
            self.components.append(in_order(completeData))

    def kit(self) -> Kit:
        kit = Kit(self)
        self.kits.append(kit)
        return kit

    def build_data_for_deploy(self):
        data_for_deploy = {}
        data_for_deploy['components'] = [{'component': c} for c in self.components]
        data_for_deploy['kits'] = []
        for kit in self.kits:
            kit_data = kit.description.copy()
            used_component_names = set()
            used_component_names.update(kit.direct_component_names)

            kit_data['boxAndComponents'] = {}
            for direct_component_name in kit.direct_component_names:
                assert direct_component_name not in kit_data['boxAndComponents']
                kit_data['boxAndComponents'][direct_component_name] = None

            for box in kit.boxes:
                box_name = box.box_component['name']
                assert box_name not in kit_data['boxAndComponents'], f"kit_data {kit_data}"
                kit_data['boxAndComponents'][box_name] = box.content_names
                used_component_names.update([box_name] + box.content_names)

            data_for_deploy['kits'].append({'kit': kit_data})

            kit_data['usedComponentNames'] = sorted(list(used_component_names))  # sort for stabilize test

        return data_for_deploy


def generate_dice(reg: ComponentRegistry):
    kit = reg.kit()

    kit.description = {
        "name": "Dice (Blue)",
        "label": "Dice (Blue)",
        "label_ja": "サイコロ（青）",
        "width": "64px",
        "height": "64px"
    }

    kit.add_component({
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
    })


def generate_playing_card(reg: ComponentRegistry):
    kit = reg.kit()

    kit.description = {
        "name": "Playing Card",
        "label": "Playing Card",
        "label_ja": "トランプ",
        "width": "400px",
        "height": "150px"
    }

    box = kit.box({
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
            box.add_component(card, template=template)
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
        box.add_component(card, template=template)
        z_index -= 1
        offset += 1

    kit.add_component({
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


def generate_psychological_safety_game(reg: ComponentRegistry):
    kit = reg.kit()

    kit.description = {
        "name": "Psychological Safety Game",
        "label": "Psychological Safety Game",
        "label_ja": "心理的安全性ゲーム",
        "width": "550px",
        "height": "750px"
    }

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
    voice_card_box = kit.box()
    for voice in range(35):
        card = {
            "name": f"PsychologicalSafety V{voice + 1:02}",
            "top": f"{offset}px",
            "left": f"{offset + 100}px",
            "faceupImage": f"/static/images/psychological_safety_v{voice + 1:02}.jpg",
            "facedownImage": "/static/images/psychological_safety_voice_back.png",
            "zIndex": z_index,
        }
        voice_card_box.add_component(card, template=template)
        z_index -= 1
        offset += 1

    offset = 0
    situation_card_box = kit.box()
    for situation in range(14):
        card = {
            "name": f"PsychologicalSafety S{situation + 1:02}",
            "top": f"{offset}px",
            "left": f"{offset + 100}px",
            "faceupImage": f"/static/images/psychological_safety_s{situation + 1:02}.jpg",
            "facedownImage": "/static/images/psychological_safety_situation_back.png",
            "zIndex": z_index,
        }
        situation_card_box.add_component(card, template=template)
        z_index -= 1
        offset += 1

    kit.add_component({
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
    voice_card_box.box_component = {
        "name": "PsychologicalSafety Box for Voice",
        "handArea": False,
        "top": "0px",
        "left": "380px",
        "height": "200px",
        "width": "350px",
        "color": "yellow",
        "text": "Situation Cards",
        "text_ja": "発言＆オプションカード",
        "textColor": "black",
        "textAlign": "center bottom",
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
    }
    z_index -= 1

    situation_card_box.box_component = {
        "name": "PsychologicalSafety Box for Situation",
        "handArea": False,
        "top": "220px",
        "left": "380",
        "height": "150px",
        "width": "350px",
        "color": "green",
        "text": "Situation Cards",
        "text_ja": "状況カード",
        "textColor": "black",
        "textAlign": "center bottom",
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
    }
    z_index -= 1

    kit.box({
        "name": "PsychologicalSafety Box for Stones",
        "handArea": False,
        "top": "390px",
        "left": "380px",
        "height": "150px",
        "width": "250px",
        "color": "black",
        "text": "Stones",
        "text_ja": "石の置き場",
        "textColor": "white",
        "textAlign": "center bottom",
        "showImage": False,
        "draggable": True,
        "flippable": False,
        "resizable": False,
        "rollable": False,
        "ownable": False,
        "traylike": True,
        "boxOfComponents": True,
        "cardistry": ['spread out', 'collect in mess'],
        "positionOfBoxContents": "random",
        "zIndex": z_index,
    }).use_components(
        [f"Transparent Stone {stone + 1:02}" for stone in range(4)] * 8
    )
    z_index -= 1


def generate_coin(reg: ComponentRegistry):
    kit = reg.kit()

    kit.description = {
        "name": "Coin - Tetradrachm of Athens",
        "label": "Coin",
        "label_ja": "コイン",
        "width": "100px",
        "height": "100px"
    }

    kit.add_component({
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
    })


def generate_stones(reg: ComponentRegistry):
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

    kit = reg.kit()
    kit.description = {
        "name": "Transparent Stones",
        "label": "Transparent Stones",
        "label_ja": "宝石(セット)",
        "positionOfKitContents": "random",
        "width": "100px",
        "height": "100px"
    }

    offset = 0
    for stone in range(4):
        s = {
            "name": f"Transparent Stone {stone + 1:02}",
            "top": f"{offset}px",
            "left": f"{offset + 100}px",
            "image": f"/static/images/transparent_stone_{stone + 1:02}.png",
        }
        kit.add_component(s, template)
        offset += 1


def generate_planning_poker(reg: ComponentRegistry):
    kit = reg.kit()

    kit.description = {
        "name": "Planning Poker",
        "label": "Planning Poker",
        "label_ja": "プランニングポーカー",
        "positionOfKitContents": "on all hand areas",
        "width": "400px",
        "height": "150px"
    }

    template = {
        "height": "40x",
        "width": "30px",
        "color": "bisque",
        "textColor": "black",
        "showImage": False,
        "facedownText": "Planning Poker",
        "faceup": True,
        "draggable": True,
        "flippable": True,
        "ownable": True,
        "resizable": False,
    }
    z_index = 100
    offset = 0
    for point in ["0", "1/2", "1", "2", "3", "5", "8", "13", "20", "40", "100", "∞", "?", "\u2615"]:
            card = {
                "name": f"PlanningPoker {point}",
                "top": f"{offset}px",
                "left": f"{offset + 100}px",
                "faceupText": f"{point}",
                "zIndex": z_index,
            }
            kit.add_component(card, template=template)
            z_index -= 1
            offset += 1


def generate_diamong_game(reg: ComponentRegistry):
    kit = reg.kit()

    kit.description = {
        "name": "Diamond Game",
        "label": "Chinese Checker",
        "label_ja": "ダイヤモンドゲーム",
        "width": "638px",
        "height": "553px"
    }

    kit.add_component({
        "name": "Diamond Game Board",
        "handArea": False,
        "top": "0",
        "left": "0",
        "height": "638px",
        "width": "553px",
        "showImage": True,
        "image": "/static/images/diamond_game_board.png",
        "draggable": True,
        "flippable": False,
        "resizable": False,
        "rollable": False,
        "ownable": False,
        "traylike": True,
        "boxOfComponents": False,
    })

    template = {
        "height": "38x",
        "width": "27px",
        "showImage": True,
        "image": "/static/images/piece_A_red.png",
        "draggable": True,
        "flippable": False,
        "ownable": False,
        "resizable": False,
    }

    INTERVAL_W = 40
    INTERVAL_H = math.sqrt(3) * (INTERVAL_W / 2)
    for i in range(5):
        for j in range(5 - i):
            piece = {
                "name": f"piece red{i}-{j}",
                "top": f"{151 + i * INTERVAL_H}px",
                "left": f"{22 + j * INTERVAL_W + (i * INTERVAL_W) / 2}px",
            }
            if i == j == 0:
                piece["name"] = "piece red king"
                piece["image"] = "/static/images/piece_A_red_king.png",
                piece["height"] = "52px"

            kit.add_component(piece, template)

    template.update({
        "image": "/static/images/piece_A_yellow.png",
    })

    for i in range(5):
        for j in range(5 - i):
            piece = {
                "name": f"piece yellow{i}-{j}",
                "top": f"{151 + i * INTERVAL_H}px",
                "left": f"{342 + j * INTERVAL_W + (i * INTERVAL_W) / 2}px",
            }
            if i == 0 and j == 4:
                piece["name"] = "piece yellow king"
                piece["image"] = "/static/images/piece_A_yellow_king.png",
                piece["height"] = "52px"
            kit.add_component(piece, template)

    template.update({
        "image": "/static/images/piece_A_green.png",
    })

    for i in range(5):
        for j in range(5 - i):
            piece = {
                "name": f"piece green{i}-{j}",
                "top": f"{433 + i * INTERVAL_H}px",
                "left": f"{181 + j * INTERVAL_W + (i * INTERVAL_W) / 2}px",
            }
            if i == 4:
                piece["name"] = "piece green king"
                piece["image"] = "/static/images/piece_A_green_king.png",
                piece["height"] = "52px"
            kit.add_component(piece, template)


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
    registry = ComponentRegistry()
    generate_dice(registry)
    generate_playing_card(registry)
    generate_psychological_safety_game(registry)
    generate_coin(registry)
    generate_stones(registry)
    generate_planning_poker(registry)
    generate_diamong_game(registry)

    with open("initial_deploy_data.json", "w", encoding="utf-8") as f:
        json.dump(registry.build_data_for_deploy(), f, indent=2)


if __name__ == "__main__":
    write_default_table_json()
    write_initial_deploy_data_json()
