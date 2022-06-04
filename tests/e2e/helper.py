from typing import Union
import re
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement

from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select

from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from selenium.common.exceptions import NoSuchElementException, TimeoutException

TOP = "http://localhost:10011/"
CUSTOMIZATION = "/customize"
STAGING_TOP = "https://fast-dusk-61776.herokuapp.com/"


def parse_style(style_str: str) -> dict:
    style = {}
    for entry in style_str.split(';'):
        try:
            key, value = entry.split(':', 1)
            style[key.strip()] = value.strip()
        except ValueError:
            continue
    return style


class Component:
    def __init__(self, helper: 'GameHelper', element: WebElement):
        self.helper = helper
        self.element = element

    def pos(self):
        """
        return position of the component relative to table
        :return: Rect(top, left)
        """
        table = self.helper.browser.find_element(by=By.CSS_SELECTOR, value="div.table")
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
            image_url = self.element.find_element(by=By.TAG_NAME, value='img').get_attribute('src')
            result.append(f"image_url: {image_url}")
        except NoSuchElementException:
            pass
        if self.element.text:
            result.append(f"text: {self.element.text}")

        return ",".join(result) or "not implemented"

    def owner(self):
        return 'box-shadow' in self.element.get_attribute('style')

    def style(self):
        return parse_style(self.element.get_attribute('style'))

    @property
    def name(self):
        return self.element.get_attribute('data-component-name')

    @property
    def z_index(self):
        return int(self.style().get('z-index', 0))

    @property
    def rotation(self):
        style = parse_style(self.element.get_attribute('style'))
        if 'transform' not in style:
            return None
        transform = style['transform']
        print(f'{transform=}')
        m = re.search(r'rotate\((\d+)deg\)', transform)
        if not m:
            return None
        return int(m.group(1))

    def __str__(self):
        return f'Component(name={self.name})'

    def __repr__(self):
        return self.__str__()


class BoxComponent(Component):
    def __init__(self, helper: 'GameHelper', element: WebElement):
        super().__init__(helper, element)

    @property
    def shuffle(self):
        return self.element.find_element(by=By.CSS_SELECTOR, value='button[data-button-name="shuffle"]')

    @property
    def spreadOut(self):
        return self.element.find_element(by=By.CSS_SELECTOR, value='button[data-button-name="spread out"]')

    @property
    def collect(self):
        return self.element.find_element(by=By.CSS_SELECTOR, value='button[data-button-name="collect"]')

    @property
    def flipAll(self):
        return self.element.find_element(by=By.CSS_SELECTOR, value='button[data-button-name="flip all"]')


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
    def add_kit(self):
        return GameMenuItem(self.browser,
                            self.browser.find_element(by=By.CSS_SELECTOR, value="div.menu div#add_remove_component"))

    @property
    def add_my_hand_area(self):
        return GameMenuItem(self.browser, self.browser.find_element(by=By.CSS_SELECTOR, value="div.menu div#add_hand_area"))

    @property
    def remove_my_hand_area(self):
        return GameMenuItem(self.browser, self.browser.find_element(by=By.CSS_SELECTOR, value="div.menu div#remove_hand_area"))

    @property
    def copy_invitation_url(self):
        return GameMenuItem(self.browser, self.browser.find_element(by=By.CSS_SELECTOR, value="div.menu a#copy_invitation_url"))

    @property
    def invitation_url(self):
        return GameMenuItem(self.browser, self.browser.find_element(by=By.CSS_SELECTOR, value="div.menu input#invitation_url"))

    @property
    def join_item(self):
        return GameMenuItem(self.browser, self.browser.find_element(by=By.CSS_SELECTOR, value="div.menu input#player_name"))

    @property
    def open_craft_box(self):
        return GameMenuItem(self.browser, self.browser.find_element(by=By.CSS_SELECTOR, value="div.menu div#open_craft_box"))

    @property
    def close_craft_box(self):
        return GameMenuItem(self.browser, self.browser.find_element(by=By.CSS_SELECTOR, value="div.menu div#close_craft_box"))

    def join(self, player_name):
        WebDriverWait(self.browser, 5).until(
            expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, "button#join_button")))
        input_element = self.browser.find_element(by=By.CSS_SELECTOR, value="input#player_name")
        join_button = self.browser.find_element(by=By.CSS_SELECTOR, value="button#join_button")
        input_element.clear()
        input_element.send_keys(player_name)
        join_button.click()
        WebDriverWait(self.browser, 5).until(
            expected_conditions.text_to_be_present_in_element((By.TAG_NAME, "body"), "you are " + player_name))

    def import_jsonfile(self, filename):
        WebDriverWait(self.browser, 5).until(
            expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, "div.menuitem#import_table")))
        self.browser.find_element(by=By.CSS_SELECTOR, value="div.menuitem#import_table").click()
        WebDriverWait(self.browser, 5).until(
            expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, "div.menu form")))
        form = self.browser.find_element(by=By.CSS_SELECTOR, value="form")
        form.find_element(by=By.CSS_SELECTOR, value="input#file").send_keys(filename)
        form.find_element(by=By.CSS_SELECTOR, value="input#submit").click()

    def add_kit_from_list(self, kit_name):
        css_selector = f"div.kit_selection div.item[data-kit-name='{kit_name}'"
        WebDriverWait(self.browser, 5).until(
            expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, css_selector)))
        item = self.browser.find_element(by=By.CSS_SELECTOR, value=css_selector)
        item.find_element(by=By.CLASS_NAME, value="add_new_component").click()

    def should_see_kit(self, kit_name):
        css_selector = f"div.kit_selection div.item[data-kit-name='{kit_name}'"
        try:
            WebDriverWait(self.browser, 5).until(
                expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, css_selector)))
        except TimeoutException:
            assert False, f'no kit named {kit_name} is visible (timeout)'

    def should_not_see_kit(self, kit_name):
        css_selector = f"div.kit_selection div.item[data-kit-name='{kit_name}'"
        try:
            WebDriverWait(self.browser, 5).until(
                expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, css_selector)))
            assert False, f'kit named {kit_name} is visible'
        except TimeoutException:
            pass

    def remove_kit_from_list(self, component_name):
        css_selector = f"div.kit_selection div.item[data-kit-name='{component_name}'"
        WebDriverWait(self.browser, 5).until(
            expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, css_selector)))
        item = self.browser.find_element(by=By.CSS_SELECTOR, value=css_selector)
        item.find_element(by=By.CLASS_NAME, value="remove_component").click()

    def add_kit_done(self):
        css_selector = f"div.kit_selection button.done"
        self.browser.find_element(by=By.CSS_SELECTOR, value=css_selector).click()


class CraftBox:
    class UploadKit:
        def __init__(self, craft_box: 'CraftBox'):
            self.craft_box = craft_box

        def select_json_file(self, filepath):
            file_input = self.craft_box.browser.find_element(by=By.CSS_SELECTOR, value='form input#data')
            file_input.send_keys(filepath)

        def select_image_files(self, filepath):
            file_input = self.craft_box.browser.find_element(by=By.CSS_SELECTOR, value='form input#images')
            file_input.send_keys(filepath)

        def upload(self):
            self.craft_box.browser.find_element(by=By.CSS_SELECTOR, value='form button#upload').click()

        def cancel(self):
            self.craft_box.browser.find_element(by=By.CSS_SELECTOR, value='form button#cancel').click()

        def accept_success_alert(self):
            self.craft_box.helper.accept_alert('Upload Success!')

        def accept_failure_alert(self):
            self.craft_box.helper.accept_alert('^Upload Failed:.*', regex_match=True)

    def __init__(self, browser: WebDriver, helper: 'GameHelper'):
        self.browser = browser
        self.helper = helper
        self.upload_kit: 'CraftBox.UploadKit' = CraftBox.UploadKit(self)
        self.export_table = object()
        self.craft_kit = object()
        self.kit_box = object()

    def use(self, tool):
        match tool:
            case self.upload_kit:
                self.helper.click_at(self.helper.component_by_name('CraftBox'), By.CSS_SELECTOR, 'button#upload_kit')
            case self.export_table:
                self.helper.click_at(self.helper.component_by_name('CraftBox'), By.CSS_SELECTOR, 'button#export_table')
            case self.craft_kit:
                self.helper.click_at(self.helper.component_by_name('CraftBox'), By.CSS_SELECTOR, 'button#craft_kit')
            case _:
                raise ValueError(f'tool {tool} is not supported')


class GameHelper:
    def __init__(self, browser: WebDriver, base_url=TOP):
        self.menu: GameMenu = GameMenu(browser)
        self.craft_box: CraftBox = CraftBox(browser, self)
        self.browser: WebDriver = browser
        self.base_url = base_url

    @staticmethod
    def player(browser, as_host=True) -> "GameHelper":
        player = GameHelper(browser)
        if as_host:
            player.go(TOP)
            player.should_have_text("you are host")
            return player
        else:
            raise RuntimeError()

    def go(self, url):
        self.browser.get(url)

    def create_table(self, prepared_table):
        self.go(self.base_url + CUSTOMIZATION)
        input_element = self.browser.find_element(by=By.CSS_SELECTOR, value="input#prepared_table")
        input_element.clear()
        input_element.send_keys(str(prepared_table))
        self.browser.find_element(by=By.CSS_SELECTOR, value="input#create").click()

    @property
    def current_url(self) -> str:
        return self.browser.current_url

    def should_have_text(self, text, timeout=5):
        try:
            WebDriverWait(self.browser, timeout).until(
                expected_conditions.text_to_be_present_in_element((By.TAG_NAME, "body"), text))
            return
        except TimeoutException:
            pass
        assert False, f'text "{text}" cannot be found (timeout)'

    def should_not_have_text(self, text, timeout=5):
        try:
            WebDriverWait(self.browser, timeout).until(
                expected_conditions.text_to_be_present_in_element((By.TAG_NAME, "body"), text))
            assert False, f'text "{text}" was found'
        except TimeoutException:
            pass

    def should_have_element(self, css_locator):
        try:
            WebDriverWait(self.browser, 5).until(
                expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, css_locator)))
            return
        except TimeoutException:
            pass
        assert False, f'element located by css locator "{css_locator}" cannot be found (timeout)'

    def should_see_component(self, name):
        selector = f'.component[data-component-name="{name}"]'
        try:
            WebDriverWait(self.browser, 5).until(
                expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, selector)))
        except TimeoutException:
            assert False, f'component "{name}" is not visible on the table (timeout)'

    def should_not_see_component(self, name):
        selector = f'.component[data-component-name="{name}"]'
        try:
            WebDriverWait(self.browser, 5).until(
                expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, selector)))
            assert False, f'component "{name}" is visible on the table'
        except TimeoutException:
            return

    def all_components(self, wait=True):
        locator = f".component"
        if wait:
            WebDriverWait(self.browser, 5).until(
                expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, locator)))
        return [Component(helper=self, element=e) for e in self.browser.find_elements(by=By.CSS_SELECTOR, value=locator)]

    def component(self, nth, wait=True) -> "Component":
        locator = f".component:nth-of-type({nth})"
        if wait:
            WebDriverWait(self.browser, 5).until(
                expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, locator)))
        return Component(helper=self, element=self.browser.find_element(by=By.CSS_SELECTOR, value=locator))

    def component_by_name(self, name, wait=True, factory=Component) -> Union["Component", BoxComponent]:
        selector = f'.component[data-component-name="{name}"]'
        if wait:
            WebDriverWait(self.browser, 5).until(
                expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, selector)))
        return factory(helper=self, element=self.browser.find_element(by=By.CSS_SELECTOR, value=selector))

    def box_by_name(self, name, wait=True) -> BoxComponent:
        return self.component_by_name(name=name, wait=wait, factory=BoxComponent)

    def count_components(self):
        selector = f'.component'
        return len(self.browser.find_elements(by=By.CSS_SELECTOR, value=selector))

    def drag(self, component: "Component", x, y, grab_at='center'):
        if grab_at == 'center':
            xoffset, yoffset = (0, 0)
        elif grab_at == 'lower right corner':
            xoffset, yoffset = (component.element.size["width"] / 2 - 1, component.element.size["height"] / 2 - 1)
        elif grab_at == 'top':
            xoffset, yoffset = (0, -(component.element.size["height"] / 2 - 1))
        elif grab_at == 'top left':
            xoffset, yoffset = (-(component.element.size["width"] / 2 - 1), -(component.element.size["height"] / 2 - 1))
        elif grab_at == 'bottom':
            xoffset, yoffset = (0, component.element.size["height"] / 2 - 1)
        elif type(grab_at) == tuple and len(grab_at) == 2:
            xoffset, yoffset = grab_at
        else:
            raise ValueError(f"grab_at '{grab_at}' is invalid")
        ActionChains(self.browser). \
            move_to_element(component.element). \
            move_by_offset(xoffset, yoffset). \
            click_and_hold(). \
            move_by_offset(x, y). \
            release(). \
            perform()

    def move_card_to_hand_area(self, card: 'Component', player_name: str, offset=(0, 0)):
        self.move_card_to_center_of_rect(card, self.hand_area(player_name).rect(), offset)

    def move_card_to_traylike(self, card: 'Component', traylike: 'Component', offset=(0, 0)):
        self.move_card_to_center_of_rect(card, traylike.rect(), offset)

    def move_card_to_center_of_rect(self, card: 'Component', rect: 'Rect', offset=(0, 0)):
        card_rect = card.rect()
        dx = (rect.left + rect.width / 2) - (card_rect.left + card_rect.width / 2) + offset[0]
        dy = (rect.top + rect.height / 2) - (card_rect.top + card_rect.height / 2) + offset[1]
        ActionChains(self.browser).move_to_element(card.element).click_and_hold().move_by_offset(dx, dy) \
            .release().perform()

    def move_mouse_by_offset(self, offset):
        ActionChains(self.browser).move_by_offset(offset[0], offset[1]).perform()

    def double_click(self, component: "Component", modifier=[]):
        chain = ActionChains(self.browser)
        if 'SHIFT' in modifier:
            chain.key_down(Keys.SHIFT)
        chain.double_click(component.element).perform()

    def click(self, component: "Component"):
        ActionChains(self.browser).click(component.element).perform()

    def click_at(self, component: "Component", by: By.ID, value: str):
        ActionChains(self.browser).click(component.element.find_element(by, value)).perform()

    def hand_area(self, owner):
        for e in self.browser.find_elements(by=By.CLASS_NAME, value="component"):
            if e.text == f"{owner}'s hand":
                return Component(self, e)
        raise NoSuchElementException(msg=f"cannot locate {owner}'s hand area")

    def accept_alert(self, text, regex_match=False):
        WebDriverWait(self.browser, 5).until(
            expected_conditions.alert_is_present())
        if regex_match:
            assert re.match(text, Alert(self.browser).text)
        else:
            assert text == Alert(self.browser).text

        Alert(self.browser).accept()

    def view_origin(self):
        table = self.browser.find_element(by=By.CSS_SELECTOR, value='div.table')
        style = parse_style(table.get_attribute('style'))
        top = int(style['top'][0:-2])  # remove px
        left = int(style['left'][0:-2])  # remove px
        return top, left


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
        return f"Rect({self.left}, {self.top}, {self.right}, {self.bottom}, {self.width}, {self.height})"

    def __repr__(self):
        return f"Rect({self.left}, {self.top}, {self.right}, {self.bottom}, {self.width}, {self.height})"

    def __eq__(self, other):
        if type(other) == Rect:
            return (self.top == other.top and self.left == other.left
                    and self.bottom == other.bottom and self.right == other.right
                    and self.height == other.height and self.width == other.width)
        if type(other) == tuple and len(other) == 2:
            return self.top == other[0] and self.left == other[1]
        return False

    def touch(self, other):
        if any([v is None for v in (self.top, self.left, self.bottom, self.right)]) or \
                any([v is None for v in (other.top, other.left, other.bottom, other.right)]):
            return True
        return not (self.bottom < other.top or other.bottom < self.top
                    or self.right < other.left or other.right < self.left)

    def within(self, area):
        if any([v is None for v in (self.top, self.left, self.bottom, self.right)]) or \
                any([v is None for v in (area.top, area.left, area.bottom, area.right)]):
            return True
        return (self.top < area.bottom and area.top < self.bottom
                and self.left < area.right and area.left < self.right)


def compo_pos(browser, element) -> Rect:
    """
    return position of the component relative to table
    :param browser: WebDriver
    :param element: component to get position
    :return: Rect(top, left)
    """
    table = browser.find_element(by=By.CSS_SELECTOR, value="div.table")
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
