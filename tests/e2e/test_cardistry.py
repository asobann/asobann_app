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
    def add_playing_card_kit(self, host, another):
        host.go(TOP)
        host.should_have_text("you are host")
        host.drag(host.component_by_name("usage"), 0, -200, 'lower right corner')
        host.menu.add_kit.execute()
        host.menu.add_kit_from_list("Playing Card")
        host.menu.add_kit_done()

    def test_shuffle_randomizes_z_index(self, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
        host = GameHelper(browser)
        another = GameHelper(another_browser)
        self.add_playing_card_kit(host, another)

        before_z_index = order_of_cards(host)
        host.box_by_name('Playing Card Box').shuffle.click()
        after_z_index = order_of_cards(host)

        average_distance = (sum([abs(before_z_index[n] - after_z_index[n]) for n in before_z_index])
                            / len(before_z_index))
        assert average_distance > 10
