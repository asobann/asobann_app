import time
from typing import Optional
import json
import requests
import pytest

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from selenium.common.exceptions import NoSuchElementException

from .helper import compo_pos, Rect, GameHelper, TOP


def test_reload_retain_player(server, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
    host = GameHelper(browser)
    host.go(TOP)

    host.should_have_text("you are host")

    invitation_url = host.menu.invitation_url.value
    # new player is invited
    player = GameHelper(another_browser)
    player.go(invitation_url)
    player.menu.join("Player A")

    # player reload and retain state
    player.go(invitation_url)
    player.should_have_text("you are Player A")
    assert not player.menu.join_item.is_visible()

    # host reload and retain state
    host.go(invitation_url)
    host.should_have_text("you are host")
    assert not host.menu.join_item.is_visible()


def test_late_comer_shall_see_the_same_table(server, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
    host = GameHelper(browser)
    host.go(TOP)
    host.drag(host.component_by_name("usage"), 0, -200, 'lower right corner')
    host.menu.add_kit.execute()
    host.menu.add_kit_from_list("Playing Card")
    host.menu.add_kit_done()

    host.should_have_text("you are host")

    # host moves a card
    card = host.component(nth=4)
    host.drag(card, x=200, y=50)
    time.sleep(0.5)
    # host.double_click(card)

    # move and resize hand area
    host.menu.add_my_hand_area.click()
    hand_area = host.hand_area(owner="host")
    host.drag(hand_area, 0, 200)
    host.drag(hand_area, 200, 30, grab_at='lower right corner')

    invitation_url = host.menu.invitation_url.value
    # new player is invited
    player = GameHelper(another_browser)
    player.go(invitation_url)
    player.should_have_text("you are observing")

    assert host.count_components() == player.count_components()

    for i in range(1, player.count_components() + 1):
        assert host.component(i).pos() == player.component(i).pos()
        assert host.component(i).size() == player.component(i).size()
        assert host.component(i).face() == player.component(i).face()


class TestOutOfSync:
    '''
    This set of test cases is to detect out-of-sync situations.
    Out-of-sync can be
    1. Two or more players see different things,
    2. A component jumps back to previous position after moving,
    or 3. Reloading browser yields different view.
    '''

    def prepare_playing_cards(self, host: GameHelper, player2: Optional[GameHelper]):
        host.go(TOP)
        host.drag(host.component_by_name("usage"), 0, -200, 'lower right corner')
        host.menu.add_kit.execute()
        host.menu.add_kit_from_list("Playing Card")
        host.menu.add_kit_done()
        host.should_have_text("you are host")

        if not player2:
            return
        player2.go(host.current_url)
        player2.menu.join("Player 2")
        player2.should_have_text("you are Player 2")

    def assert_seeing_same(self, player1: GameHelper, player2: GameHelper):
        def assert_components_sync():
            components1 = player1.all_components()
            components2 = player2.all_components()
            assert len(components1) == len(components2)
            for i in range(len(components1)):
                assert components1[i].rect() == components2[i].rect(), f'name={components1[i].name}'
                assert components1[i].face() == components2[i].face(), f'name={components1[i].name}'
                assert components1[i].owner() == components2[i].owner(), f'name={components1[i].name}'
                assert components1[i].style().get('zIndex', None) == components2[i].style().get('zIndex', None), \
                    f'name={components1[i].name}'

        assert_components_sync()

        player2.browser.refresh()
        assert_components_sync()

    def test_single_card(self, server, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
        host = GameHelper(browser)
        player2 = GameHelper(another_browser)
        self.prepare_playing_cards(host, player2)

        host.drag(host.component_by_name('PlayingCard S_A'), 30, 100)
        host.double_click(host.component_by_name('PlayingCard S_A'))

        self.assert_seeing_same(host, player2)

    def test_move_box_of_card_bit_by_bit(self, server, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
        host = GameHelper(browser)
        player2 = GameHelper(another_browser)
        self.prepare_playing_cards(host, player2)

        host.drag(host.component_by_name('Playing Card Box'), 20, 20, grab_at=(0, 80))
        host.drag(host.component_by_name('Playing Card Box'), 20, 20, grab_at=(0, 80))
        host.drag(host.component_by_name('Playing Card Box'), 20, 20, grab_at=(0, 80))
        host.drag(host.component_by_name('Playing Card Box'), 20, 20, grab_at=(0, 80))
        host.drag(host.component_by_name('Playing Card Box'), 20, 20, grab_at=(0, 80))

        self.assert_seeing_same(host, player2)

    def test_move_box_of_card_long(self, server, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
        host = GameHelper(browser)
        player2 = GameHelper(another_browser)
        self.prepare_playing_cards(host, player2)

        host.drag(host.component_by_name('Playing Card Box'), 200, 200, grab_at=(0, 80))

        self.assert_seeing_same(host, player2)

    def test_a_card_on_hand_area(self, server, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
        host = GameHelper(browser)
        player2 = GameHelper(another_browser)
        self.prepare_playing_cards(host, player2)

        host.menu.add_my_hand_area.click()
        host.move_card_to_hand_area(host.component_by_name("PlayingCard S_A"), 'host')
        host.drag(host.hand_area('host'), 50, 100, grab_at=(60, 0))

        self.assert_seeing_same(host, player2)

    def test_order_of_updates_at_server(self, debug_order_of_updates, server, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
        host = GameHelper(browser)
        player2 = GameHelper(another_browser)
        self.prepare_playing_cards(host, player2)
        host.drag(host.component_by_name('Playing Card Box'), 200, 200, grab_at=(0, 80))
        host.drag(host.component_by_name('Playing Card Box'), -200, -200, grab_at=(0, 80))
        host.drag(host.component_by_name('Playing Card Box'), 500, 500, grab_at=(0, 80))
        host.drag(host.component_by_name('Playing Card Box'), -500, -500, grab_at=(0, 80))
        host.drag(host.component_by_name('Playing Card Box'), 200, 200, grab_at=(0, 80))
        host.drag(host.component_by_name('Playing Card Box'), -200, -200, grab_at=(0, 80))
        host.drag(host.component_by_name('Playing Card Box'), 500, 500, grab_at=(0, 80))
        host.drag(host.component_by_name('Playing Card Box'), -500, -500, grab_at=(0, 80))

        res = requests.get(TOP + '/debug/get_log_of_updates')
        order_of_updates = json.loads(res.content)
        for browser in order_of_updates.keys():
            for component_id in order_of_updates[browser]:
                log = order_of_updates[browser][component_id]
                for i in range(len(log) - 1):
                    assert log[i]['epoch'] <= log[i + 1]['epoch']

        self.assert_seeing_same(host, player2)
