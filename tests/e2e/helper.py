from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement

from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from selenium.common.exceptions import NoSuchElementException, TimeoutException

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


class Rect:
    top: float
    left: float
    bottom: float
    right: float
    height: float
    width: float

    def __init__(self, top=None, left=None, bottom=None, right=None, height=None, width=None):
        self.top = top
        self.left = left
        self.bottom = bottom
        self.right = right
        self.height = height
        self.width = width

    def __str__(self):
        return f"Rect(top={self.top}, left={self.left}, bottom={self.bottom}, right={self.right}, height={self.height}, width={self.width})"

    def __eq__(self, other):
        if type(other) != Rect:
            return False
        return (self.top == other.top and self.left == other.left
                and self.bottom == other.bottom and self.right == other.right
                and self.height == other.height and self.width == other.width)


def compo_pos(browser, component) -> Rect:
    """
    return position of the component relative to table
    :param browser: WebDriver
    :param component: component to get position
    :return: { "top": Number, "left": Number }
    """
    table = browser.find_element_by_css_selector("div.table")
    table_loc = table.location
    comp_loc = component.location
    return Rect(left=comp_loc["x"] - table_loc["x"], top=comp_loc["y"] - table_loc["y"])


