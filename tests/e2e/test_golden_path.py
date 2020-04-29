import pytest

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from selenium.common.exceptions import NoSuchElementException, TimeoutException

from .helper import compo_pos, Rect

TOP = "http://localhost:10011/"


def test_golden_path(server, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
    browser.get(TOP)

    # index
    assert "play card game" in browser.find_element_by_tag_name("body").text
    browser.find_element_by_name("player").clear()
    browser.find_element_by_name("player").send_keys("test-player-A")
    browser.find_element_by_tag_name("form").submit()

    # creating and joining new game
    WebDriverWait(browser, 5).until(
        expected_conditions.text_to_be_present_in_element((By.TAG_NAME, "body"), "you are test-player-A"))
    WebDriverWait(browser, 5).until(
        expected_conditions.presence_of_element_located((By.CSS_SELECTOR, "div.table")))

    # handle cards
    card = browser.find_element_by_css_selector(".component:nth-of-type(3)")
    assert Rect(left=150, top=175) == compo_pos(browser, card)
    ActionChains(browser).move_to_element(card).move_by_offset(10, 10).click_and_hold().move_by_offset(300,
                                                                                                       50).release().perform()
    assert Rect(left=450, top=225) == compo_pos(browser, card)
    assert "voice_back.png" in card.find_element_by_tag_name('img').get_attribute('src')
    ActionChains(browser).double_click(card).perform()
    assert "v02.jpg" in card.find_element_by_tag_name('img').get_attribute('src')

    # open another browser and see the same cards
    another_browser.get(browser.current_url)
    WebDriverWait(another_browser, 5).until(
        expected_conditions.presence_of_element_located((By.CSS_SELECTOR, ".component:nth-of-type(3)")))
    card_on_another_browser = another_browser.find_element_by_css_selector(".component:nth-of-type(3)")
    assert Rect(left=450, top=225) == compo_pos(browser, card_on_another_browser)
    assert "v02.jpg" in card_on_another_browser.find_element_by_tag_name('img').get_attribute('src')


class GameHelper:

    def __init__(self, browser):
        self.browser = browser

    def go(self, url):
        self.browser.get(url)

    def should_have_text(self, text):
        try:
            WebDriverWait(self.browser, 5).until(
                expected_conditions.text_to_be_present_in_element((By.TAG_NAME, "body"), "text"))
            return
        except TimeoutException:
            pass
        assert False, f'text "{text}" cannot be found (timeout)'

    def components(self, nth):
        return self.browser.find_element_by_css_selector(f".component:nth-of-type({nth})")

    def drag(self, component, x, y):
        ActionChains(self.browser).move_to_element(component).click_and_hold().move_by_offset(x, y).release().perform()

    def double_click(self, component):
        ActionChains(self.browser).double_click(component).perform()


class Component:
    def __init__(self, helper: GameHelper, element):
        self.helper = helper
        self.element = element

    def pos(self):
        return compo_pos(self.helper.browser, self.element)

    def face(self):
        return "not implemented"


def test_table_host(server, browser: webdriver.Firefox):
    host = GameHelper(browser)
    host.go(TOP)

    host.should_have_text("your are host")

    # host can move cards
    card = host.components(nth=2)
    card_pos = card.pos()
    host.drag(card, x=200, y=50)
    assert card_pos.left + 200 == card.pos().left and  card_pos.top + 50 == card.pos().top
    face = card.face()
    host.double_click(card)
    assert face != card.face()


if __name__ == '__main__':
    test_golden_path()
