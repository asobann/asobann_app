import pytest

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement

from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from selenium.common.exceptions import NoSuchElementException, TimeoutException

from .helper import compo_pos, Rect, GameHelper

TOP = "http://localhost:10011/"


def test_golden_path(server, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
    host = GameHelper(browser)
    host.go(TOP)

    # index
    WebDriverWait(browser, 5).until(
        expected_conditions.presence_of_element_located((By.CSS_SELECTOR, "div.table")))

    # handle cards
    card = host.components(3)
    assert Rect(left=150, top=175) == card.pos()
    host.drag(card, x=300, y=50)
    assert Rect(left=450, top=225) == card.pos()
    assert "voice_back.png" in card.element.find_element_by_tag_name('img').get_attribute('src')
    host.double_click(card)
    assert "v02.jpg" in card.element.find_element_by_tag_name('img').get_attribute('src')

    # open another browser and see the same cards
    another = GameHelper(another_browser)
    another.go(browser.current_url)
    card_on_another_browser = another.components(3)
    assert Rect(left=450, top=225) == card_on_another_browser.pos()
    assert "v02.jpg" in card_on_another_browser.element.find_element_by_tag_name('img').get_attribute('src')


def test_table_host(server, browser: webdriver.Firefox):
    host = GameHelper(browser)
    host.go(TOP)

    host.should_have_text("you are host")

    # host can move cards
    card = host.components(nth=4)
    card_pos = card.pos()
    host.drag(card, x=200, y=50)
    assert card_pos.left + 200 == card.pos().left and  card_pos.top + 50 == card.pos().top
    face = card.face()
    host.double_click(card)
    assert face != card.face()


if __name__ == '__main__':
    test_golden_path()
