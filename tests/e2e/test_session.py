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
