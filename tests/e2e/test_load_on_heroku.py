from pathlib import Path

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from selenium.common.exceptions import NoSuchElementException

from .helper import compo_pos, Rect, GameHelper

TOP = "https://fast-dusk-61776.herokuapp.com/"


def test_reload_retain_player(server, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
    host = GameHelper(browser)
    host.go(TOP)

    host.menu.import_jsonfile(str(Path(__file__).parent / "./test_load_on_heroku.json"))

    host.should_have_text("you are host")
    host.should_have_text("Table for load testing")

    invitation_url = host.menu.invitation_url.value
    # new player is invited
    player = GameHelper(another_browser)
    player.go(invitation_url)
    player.menu.join("Player A")
