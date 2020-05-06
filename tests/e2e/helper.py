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

    def execute(self):
        self.element.click()

    @property
    def value(self):
        return self.element.get_attribute("value")

    def is_visible(self):
        return self.element.is_displayed()


class GameMenu:
    def __init__(self, browser: WebDriver):
        self.browser = browser

    @property
    def add_component(self):
        return GameMenuItem(self.browser,
                            self.browser.find_element_by_css_selector("div.menu div#add_remove_component"))

    @property
    def add_my_hand_area(self):
        return GameMenuItem(self.browser, self.browser.find_element_by_css_selector("div.menu div#add_hand_area"))

    @property
    def copy_invitation_url(self):
        return GameMenuItem(self.browser, self.browser.find_element_by_css_selector("div.menu a#copy_invitation_url"))

    @property
    def invitation_url(self):
        return GameMenuItem(self.browser, self.browser.find_element_by_css_selector("div.menu input#invitation_url"))

    @property
    def join_item(self):
        return GameMenuItem(self.browser, self.browser.find_element_by_css_selector("div.menu input#player_name"))

    def join(self, player_name):
        WebDriverWait(self.browser, 5).until(
            expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, "button#join_button")))
        input_element = self.browser.find_element_by_css_selector("input#player_name")
        join_button = self.browser.find_element_by_css_selector("button#join_button")
        input_element.clear()
        input_element.send_keys(player_name)
        join_button.click()
        WebDriverWait(self.browser, 5).until(
            expected_conditions.text_to_be_present_in_element((By.TAG_NAME, "body"), "you are " + player_name))

    def import_jsonfile(self, filename):
        WebDriverWait(self.browser, 5).until(
            expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, "div.menuitem#import_table")))
        self.browser.find_element_by_css_selector("div.menuitem#import_table").click()
        WebDriverWait(self.browser, 5).until(
            expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, "div.menu form")))
        form = self.browser.find_element_by_css_selector("form")
        form.find_element_by_css_selector("input#file").send_keys(filename)
        form.find_element_by_css_selector("input#submit").click()

    def add_component_from_list(self, component_name):
        css_selector = f"div.component_selection div.item[data-component-name='{component_name}'"
        WebDriverWait(self.browser, 5).until(
            expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, css_selector)))
        item = self.browser.find_element_by_css_selector(css_selector)
        item.find_element_by_class_name("add_new_component").click()


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

    def component(self, nth, wait=True) -> "Component":
        locator = f".component:nth-of-type({nth})"
        if wait:
            WebDriverWait(self.browser, 5).until(
                expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, locator)))
        return Component(helper=self, element=self.browser.find_element_by_css_selector(locator))

    def component_by_name(self, name, wait=True) -> "Component":
        selector = f'.component[data-component-name="{name}"]'
        if wait:
            WebDriverWait(self.browser, 5).until(
                expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, selector)))
        return Component(helper=self, element=self.browser.find_element_by_css_selector(selector))

    def drag(self, component: "Component", x, y, pos='center'):
        if pos == 'center':
            xoffset, yoffset = (0, 0)
        elif pos == 'lower right corner':
            xoffset, yoffset = (component.element.size["width"] / 2 - 1, component.element.size["height"] / 2 - 1)
        else:
            raise ValueError(f"pos '{pos}' is invalid")
        ActionChains(self.browser). \
            move_to_element(component.element). \
            move_by_offset(xoffset, yoffset). \
            click_and_hold(). \
            move_by_offset(x, y). \
            release(). \
            perform()

    def move_card_to_hand_area(self, card: 'Component', player_name: str, offset=(0, 0)):
        hand_area_rect = self.hand_area(player_name).rect()
        card_rect = card.rect()
        dx = (hand_area_rect.left + hand_area_rect.width / 2) - (card_rect.left + card_rect.width / 2) + offset[0]
        dy = (hand_area_rect.top + hand_area_rect.height / 2) - (card_rect.top + card_rect.height / 2) + offset[1]
        ActionChains(self.browser).move_to_element(card.element).click_and_hold().move_by_offset(dx, dy) \
            .release().perform()

    def double_click(self, component: "Component"):
        ActionChains(self.browser).double_click(component.element).perform()

    def click(self, component: "Component"):
        ActionChains(self.browser).click(component.element).perform()

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
        """
        return position of the component relative to table
        :return: Rect(top, left)
        """
        table = self.helper.browser.find_element_by_css_selector("div.table")
        table_loc = table.location
        comp_loc = self.element.location
        return Rect(left=comp_loc["x"] - table_loc["x"], top=comp_loc["y"] - table_loc["y"])

    def size(self):
        """
        return size of the component
        :return: Rect(height, width)
        """
        comp_size = self.element.size
        return Rect(height=comp_size["height"], width=comp_size["width"])

    def rect(self):
        """
        return rect of the component
        :return: Rect(left, top, right, bottom, height, width)
        """
        pos = self.pos()
        size = self.size()
        return Rect(left=pos.left, top=pos.top,
                    right=pos.left + size.width, bottom=pos.top + size.height,
                    width=size.width, height=size.height)

    def face(self):
        result = []
        try:
            image_url = self.element.find_element_by_tag_name('img').get_attribute('src')
            result.append(f"image_url : {image_url}")
        except NoSuchElementException:
            pass
        if self.element.text:
            result.append(f"text : {self.element.text}")

        return ",".join(result) or "not implemented"


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
        return f"Rect({self.top}, {self.left}, {self.bottom}, {self.right}, {self.height}, {self.width})"

    def __repr__(self):
        return f"Rect({self.top}, {self.left}, {self.bottom}, {self.right}, {self.height}, {self.width})"

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
