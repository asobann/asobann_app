import pytest

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement

from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from selenium.common.exceptions import NoSuchElementException, TimeoutException

from .helper import compo_pos, Rect

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


class GameHelper:

    def __init__(self, browser):
        self.browser = browser

    def go(self, url):
        self.browser.get(url)

    def should_have_text(self, text):
        try:
            WebDriverWait(self.browser, 5).until(
                expected_conditions.text_to_be_present_in_element((By.TAG_NAME, "body"), text))
            return
        except TimeoutException:
            pass
        assert False, f'text "{text}" cannot be found (timeout)'

    def should_have_element(self, css_locator):
        try:
            WebDriverWait(self.browser, 5).until(
                expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, css_locator)))
            return
        except TimeoutException:
            pass
        assert False, f'element located by css locator "{css_locator}" cannot be found (timeout)'

    def components(self, nth):
        locator = f".component:nth-of-type({nth})"
        WebDriverWait(self.browser, 5).until(
            expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, locator)))
        return Component(helper=self, element=self.browser.find_element_by_css_selector(locator))

    def drag(self, component: "Component", x, y):
        ActionChains(self.browser).move_to_element(component.element).click_and_hold().move_by_offset(x, y).release().perform()

    def double_click(self, component: "Component"):
        ActionChains(self.browser).double_click(component.element).perform()


class Component:
    def __init__(self, helper: GameHelper, element: WebElement):
        self.helper = helper
        self.element = element

    def pos(self):
        return compo_pos(self.helper.browser, self.element)

    def face(self):
        if self.element.find_element_by_tag_name('img'):
            image_url = self.element.find_element_by_tag_name('img').get_attribute('src')
            return f"image_url : {image_url}"

        return "not implemented"


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
