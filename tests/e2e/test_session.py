import time

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

    assert host.count_components() == player.count_components() == 58

    for i in range(1, 59):
        assert host.component(i).pos() == player.component(i).pos()
        assert host.component(i).size() == player.component(i).size()
        assert host.component(i).face() == player.component(i).face()
