import pytest
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from selenium.common.exceptions import NoSuchElementException

from .helper import compo_pos, Rect, GameHelper, STAGING_TOP


def test_create_empty_table(server, browser: webdriver.Firefox):
    host = GameHelper(browser)
    host.create_table(0)

    host.should_have_text("you are host")

    assert host.count_components() == 0


def test_load_playing_card_kit(server, browser: webdriver.Firefox):
    host = GameHelper(browser)
    host.create_table(0)

    host.should_have_text("you are host")

    host.menu.add_kit.execute()
    host.menu.add_kit_from_list("Playing Card")

    assert host.count_components() == 52 + 2 + 1

    assert host.component_by_name("PlayingCard S_A").pos() == (64, 164)
    host.drag(host.component_by_name("Playing Card Box"), 200, 100, grab_at=(-70, 0))
    assert host.component_by_name("PlayingCard S_A").pos() == (64 + 100, 164 + 200)


def test_load_and_remove_playing_card_kit(server, browser: webdriver.Firefox):
    host = GameHelper(browser)
    host.create_table(0)

    host.should_have_text("you are host")

    host.menu.add_kit.execute()
    host.menu.add_kit_from_list("Playing Card")
    host.menu.remove_kit_from_list("Playing Card")
    host.menu.add_kit_from_list("Playing Card")

    assert host.component_by_name("PlayingCard S_A").pos() == (64, 164)
    host.drag(host.component_by_name("Playing Card Box"), 200, 100, grab_at=(-70, 0))
    assert host.component_by_name("PlayingCard S_A").pos() == (64 + 100, 164 + 200)


@pytest.mark.loadtest
def test_load_playing_card_kit_on_staging(server, browser: webdriver.Firefox):
    host = GameHelper(browser)
    host.go(STAGING_TOP + "/customize")
    input_element = host.browser.find_element_by_css_selector("input#prepared_table")
    input_element.clear()
    input_element.send_keys("0")
    host.browser.find_element_by_css_selector("input#create").click()

    host.should_have_text("you are host")

    host.menu.add_kit.execute()
    host.menu.add_kit_from_list("Playing Card")

    time.sleep(1)
    assert host.count_components() == 52 + 2 + 1

    assert host.component_by_name("PlayingCard S_A").pos() == (64, 164)
    host.drag(host.component_by_name("Playing Card Box"), 200, 100, grab_at=(70, 0))
    assert host.component_by_name("PlayingCard S_A").pos() == (64 + 200, 164 + 100)


@pytest.mark.skip
def test_shuffle_playing_card():
    pass
