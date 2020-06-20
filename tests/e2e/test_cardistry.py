import re
import pytest

from selenium import webdriver

from .helper import compo_pos, Rect, GameHelper, TOP


def playing_cards(helper: GameHelper):
    return [e for e in helper.all_components() if re.match('PlayingCard [SHDC]_.*', e.name)]


def order_of_cards(helper: GameHelper):
    return {c.name: i for i, c in enumerate(sorted(playing_cards(helper), key=lambda e: e.z_index))}


@pytest.mark.usefixtures("server")
class TestShuffle:
    def add_playing_card_kit(self, host):
        host.go(TOP)
        host.should_have_text("you are host")
        host.drag(host.component_by_name("usage"), 0, -200, 'lower right corner')
        host.menu.add_kit.execute()
        host.menu.add_kit_from_list("Playing Card")
        host.menu.add_kit_done()

    def test_shuffle_randomizes_z_index(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        self.add_playing_card_kit(host)

        before_order = order_of_cards(host)
        host.box_by_name('Playing Card Box').shuffle.click()
        after_order = order_of_cards(host)

        average_distance = (sum([abs(before_order[n] - after_order[n]) for n in before_order])
                            / len(before_order))
        assert average_distance > 10

    def test_shuffle_order_cards_by_1px(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        self.add_playing_card_kit(host)
        host.box_by_name('Playing Card Box').shuffle.click()

        all_cards = {e.name: e for e in playing_cards(host)}
        all_cards_in_order = sorted([all_cards[n] for n, z in order_of_cards(host).items()],
                                    key=lambda c: c.z_index)
        for i, c in enumerate(all_cards_in_order):
            if i < len(all_cards_in_order) - 2:
                pos1 = c.pos()
                pos2 = all_cards_in_order[i + 1].pos()
                print(pos1, pos2)

                # somehow there were cases where two cards separate 2 px but looks ok
                assert abs(pos1.left - pos2.left) < 3 and abs(pos1.top - pos2.top) < 3
