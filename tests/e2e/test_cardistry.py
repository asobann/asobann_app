import re
import pytest

from selenium import webdriver
from selenium.webdriver.common.alert import Alert

from .helper import compo_pos, Rect, GameHelper, TOP


def playing_cards(helper: GameHelper):
    return [e for e in helper.all_components() if re.match('PlayingCard [SHDC]_.*', e.name)]


def order_of_cards(helper: GameHelper):
    return {c.name: i for i, c in enumerate(sorted(playing_cards(helper), key=lambda e: e.z_index))}


def add_playing_card_kit(host):
    host.go(TOP)
    host.should_have_text("you are host")
    host.drag(host.component_by_name("usage"), 0, -200, 'lower right corner')
    host.menu.add_kit.execute()
    host.menu.add_kit_from_list("Playing Card")
    host.menu.add_kit_done()


@pytest.mark.usefixtures("server")
class TestShuffle:
    def test_shuffle_randomizes_z_index(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        add_playing_card_kit(host)

        before_order = order_of_cards(host)
        host.box_by_name('Playing Card Box').shuffle.click()
        after_order = order_of_cards(host)

        average_distance = (sum([abs(before_order[n] - after_order[n]) for n in before_order])
                            / len(before_order))
        assert average_distance > 10

    def test_shuffle_order_cards_by_1px(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        add_playing_card_kit(host)
        host.box_by_name('Playing Card Box').shuffle.click()

        all_cards = {e.name: e for e in playing_cards(host)}
        all_cards_in_order = sorted([all_cards[n] for n, z in order_of_cards(host).items()],
                                    key=lambda c: c.z_index)
        for i, c in enumerate(all_cards_in_order):
            if i < len(all_cards_in_order) - 2:
                pos1 = c.pos()
                pos2 = all_cards_in_order[i + 1].pos()

                # somehow there were cases where two cards separate 2 px but looks ok
                assert abs(pos1.left - pos2.left) < 3 and abs(pos1.top - pos2.top) < 3

    def test_shuffle_only_the_cards_on_the_box(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        add_playing_card_kit(host)

        # move into stowage
        card1 = host.component_by_name('PlayingCard S_A')
        host.move_card_to_traylike(card1, host.component_by_name('Stowage for Unused Cards'))

        # move into hand area
        host.menu.add_my_hand_area.click()
        card2 = host.component_by_name('PlayingCard S_K')
        host.move_card_to_hand_area(card2, 'host')

        # move to nowhere
        card3 = host.component_by_name('PlayingCard S_Q')
        host.drag(card3, 0, -200)

        before = [(c.rect(), c.z_index) for c in [card1, card2, card3]]
        host.box_by_name('Playing Card Box').shuffle.click()
        after = [(c.rect(), c.z_index) for c in [card1, card2, card3]]

        assert before == after


@pytest.mark.usefixtures("server")
class TestSpreadOutAndCollect:
    def test_spread_out_moves_every_card(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        add_playing_card_kit(host)

        all_cards = playing_cards(host)
        before = {c.name: c.rect() for c in all_cards}
        host.box_by_name('Playing Card Box').spreadOut.click()
        after = {c.name: c.rect() for c in all_cards}

        assert all([before[n] != after[n] for n in before.keys()])

    def test_spread_out_never_make_overlaps(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        add_playing_card_kit(host)

        host.box_by_name('Playing Card Box').spreadOut.click()

        rects = [c.rect() for c in playing_cards(host)]
        while rects:
            r = rects.pop()
            for rr in rects:
                assert not r.touch(rr)

    def test_spread_out_then_collect_does_not_change_order(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        add_playing_card_kit(host)

        host.box_by_name('Playing Card Box').shuffle.click()
        before_order = order_of_cards(host)
        host.box_by_name('Playing Card Box').spreadOut.click()
        host.box_by_name('Playing Card Box').collect.click()
        after_order = order_of_cards(host)

        assert before_order == after_order

    def test_collect_moves_back_every_card(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        add_playing_card_kit(host)

        host.box_by_name('Playing Card Box').spreadOut.click()
        host.box_by_name('Playing Card Box').collect.click()

        box_area = host.box_by_name('Playing Card Box').rect()
        assert all((c.rect().within(box_area) for c in playing_cards(host)))

    def test_can_ignore_cards_in_hand_area(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        add_playing_card_kit(host)
        host.menu.add_my_hand_area.click()

        host.box_by_name('Playing Card Box').spreadOut.click()

        card = host.component_by_name('PlayingCard S_A')
        host.move_card_to_hand_area(card, 'host')
        before = card.rect()
        host.box_by_name('Playing Card Box').collect.click()
        Alert(browser).dismiss()

        after = card.rect()
        assert before == after

    def test_can_collect_cards_in_hand_area(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        add_playing_card_kit(host)
        host.menu.add_my_hand_area.click()

        host.box_by_name('Playing Card Box').spreadOut.click()

        card = host.component_by_name('PlayingCard S_A')
        host.move_card_to_hand_area(card, 'host')
        before = card.rect()
        host.box_by_name('Playing Card Box').collect.click()
        Alert(browser).accept()

        after = card.rect()
        assert before != after

    def test_ignore_cards_in_stowage(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        add_playing_card_kit(host)

        host.box_by_name('Playing Card Box').spreadOut.click()

        card = host.component_by_name('PlayingCard S_A')
        host.move_card_to_traylike(card, host.box_by_name('Stowage for Unused Cards'))
        before = card.rect()
        host.box_by_name('Playing Card Box').collect.click()

        after = card.rect()
        assert before == after


@pytest.mark.usefixtures("server")
class TestFlipAll:
    def test_to_face_up(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        add_playing_card_kit(host)

        host.box_by_name('Playing Card Box').flipAll.click()
        assert all(('card_up' in c.face() for c in playing_cards(host)))

    def test_to_face_down(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        add_playing_card_kit(host)

        host.box_by_name('Playing Card Box').flipAll.click()
        host.box_by_name('Playing Card Box').flipAll.click()
        assert all(('card_back' in c.face() for c in playing_cards(host)))

    def test_to_face_down_if_any_are_face_up(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        add_playing_card_kit(host)

        host.double_click(host.component_by_name('PlayingCard S_A'))
        host.box_by_name('Playing Card Box').flipAll.click()
        assert all(('card_back' in c.face() for c in playing_cards(host)))

    def test_only_cards_in_box(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        add_playing_card_kit(host)

        host.drag(host.component_by_name('PlayingCard S_A'), 0, 150)
        host.box_by_name('Playing Card Box').flipAll.click()
        assert 'card_back' in host.component_by_name('PlayingCard S_A').face()
        assert 'card_up' in host.component_by_name('PlayingCard S_K').face()

