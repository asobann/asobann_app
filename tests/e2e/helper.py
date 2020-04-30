from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement

from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from selenium.common.exceptions import NoSuchElementException, TimeoutException


TOP = "http://localhost:10011/"


class GameMenuItem:
    def __init__(self, browser: WebDriver, element: WebElement):
        self.browser = browser
        self.element = element

    def click(self):
        self.element.click()

    @property
    def value(self):
        return self.element.get_attribute("value")


class GameMenu:
    def __init__(self, browser: WebDriver):
        self.browser = browser

    @property
    def add_my_hand_area(self):
        return GameMenuItem(self.browser, self.browser.find_element_by_css_selector("div.menu div#add_hand_area"))

    @property
    def copy_invitation_url(self):
        return GameMenuItem(self.browser, self.browser.find_element_by_css_selector("div.menu a#copy_invitation_url"))

    @property
    def invitation_url(self):
        return GameMenuItem(self.browser, self.browser.find_element_by_css_selector("div.menu input#invitation_url"))

    def join(self, player_name):
        WebDriverWait(self.browser, 5).until(
            expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, "button#join_button")))
        input_element = self.browser.find_element_by_css_selector("input#player_name")
        join_button = self.browser.find_element_by_css_selector("button#join_button")
        input_element.clear()
        ActionChains(self.browser).click(input_element).send_keys(player_name).click(join_button).perform()


class GameHelper:

    def __init__(self, browser: WebDriver):
        self.menu = GameMenu(browser)
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

    def drag(self, component: "Component", x, y, pos='center'):
        if pos == 'center':
            xoffset, yoffset = (0, 0)
        elif pos == 'lower right corner':
            xoffset, yoffset = (component.element.size["width"] / 2 - 1, component.element.size["height"] / 2 - 1)
        else:
            raise ValueError(f"pos '{pos}' is invalid")
        ActionChains(self.browser).\
            move_to_element(component.element).\
            move_by_offset(xoffset, yoffset).\
            click_and_hold().\
            move_by_offset(x, y).\
            release().\
            perform()

    def double_click(self, component: "Component"):
        ActionChains(self.browser).double_click(component.element).perform()

    def hand_area(self, owner):
        for e in self.browser.find_elements_by_class_name("component"):
            if e.text == f"{owner}'s hand":
                return Component(self, e)
        raise NoSuchElementException(msg=f"cannot locate {owner}'s hand area")


class Component:
    def __init__(self, helper: GameHelper, element: WebElement):
        self.helper = helper
        self.element = element

    def pos(self):
        return compo_pos(self.helper.browser, self.element)

    def size(self):
        return compo_size(self.helper.browser, self.element)

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

    def __repr__(self):
        return f"Rect(top={self.top}, left={self.left}, bottom={self.bottom}, right={self.right}, height={self.height}, width={self.width})"

    def __eq__(self, other):
        if type(other) != Rect:
            return False
        return (self.top == other.top and self.left == other.left
                and self.bottom == other.bottom and self.right == other.right
                and self.height == other.height and self.width == other.width)


def compo_pos(browser, element) -> Rect:
    """
    return position of the component relative to table
    :param browser: WebDriver
    :param element: component to get position
    :return: Rect(top, left)
    """
    table = browser.find_element_by_css_selector("div.table")
    table_loc = table.location
    comp_loc = element.location
    return Rect(left=comp_loc["x"] - table_loc["x"], top=comp_loc["y"] - table_loc["y"])


def compo_size(browser, element: WebElement) -> Rect:
    """
    return size of the component
    :param browser: WebDriver
    :param element: component to get size
    :return: Rect(height, width)
    """
    comp_size = element.size
    return Rect(height=comp_size["height"], width=comp_size["width"])


