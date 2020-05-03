import pytest

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from selenium.common.exceptions import NoSuchElementException

from .helper import compo_pos, Rect, GameHelper, TOP


def rect(element):
    return {
        'top': element.location["y"],
        'left': element.location["x"],
        'bottom': element.location["y"] + element.size["height"],
        'right': element.location["x"] + element.size["width"],
        'height': element.size["height"],
        'width': element.size["width"],
    }


def test_add_and_move_hand_area(server, browser: webdriver.Firefox):
    host = GameHelper(browser)
    host.go(TOP)

    host.should_have_text("you are host")
    host.menu.add_my_hand_area.click()

    # move and resize hand area
    hand_area = host.hand_area(owner="host")
    host.drag(hand_area, 0, 200)
    size = hand_area.size()
    host.drag(hand_area, 200, 30, pos='lower right corner')
    assert size.width + 200 == hand_area.size().width and size.height + 30 == hand_area.size().height


def test_put_cards_in_hand(server, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
    host = GameHelper(browser)
    host.go(TOP)

    host.should_have_text("you are host")
    host.menu.add_my_hand_area.click()

    # creating and joining new game
    WebDriverWait(browser, 5).until(
        expected_conditions.presence_of_element_located((By.CSS_SELECTOR, "div.component:nth-of-type(5)")))

    hand_area = browser.find_element_by_css_selector(".component:nth-of-type(5)")
    ActionChains(browser).move_to_element(hand_area).click_and_hold().move_by_offset(0, 50).release().perform()
    hand_area_rect = rect(hand_area)
    card = browser.find_element_by_css_selector(".component:nth-of-type(3)")
    card_rect = rect(card)
    ActionChains(browser).move_to_element(card).click_and_hold().move_by_offset(
        hand_area_rect["left"] - card_rect["left"], hand_area_rect["top"] - card_rect["left"]).release().perform()

    another = GameHelper(another_browser)
    another.go(browser.current_url)
    another.menu.join("Player 2")
    WebDriverWait(another_browser, 5).until(
        expected_conditions.presence_of_element_located((By.CSS_SELECTOR, "div.component:nth-of-type(5)")))
    card_on_another = another_browser.find_element_by_css_selector(".component:nth-of-type(3)")
    card_pos_before_drag = compo_pos(another_browser, card_on_another)
    ActionChains(another_browser).move_to_element(card_on_another).click_and_hold().move_by_offset(50, 50).perform()
    assert card_pos_before_drag == compo_pos(another_browser, card_on_another), "not moved"


@pytest.mark.usefixtures("server")
class TestDice:
    def test_add_dice_from_menu(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        host.go(TOP)
        host.should_have_text("you are host")

        host.menu.add_component.execute()
        host.menu.check_component_from_list("dice")
        host.menu.update.execute()

        assert host.components_by_name("dice")