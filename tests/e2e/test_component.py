from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from selenium.common.exceptions import NoSuchElementException
from .helper import compo_pos


def rect(element):
    return {
        'top': element.location["y"],
        'left': element.location["x"],
        'bottom': element.location["y"] + element.size["height"],
        'right': element.location["x"] + element.size["width"],
        'height': element.size["height"],
        'width': element.size["width"],
    }


def test_move_hand_area(server, browser: webdriver.Firefox):
    browser.get("http://localhost:10011/")
    # index
    browser.find_element_by_name("player").clear()
    browser.find_element_by_name("player").send_keys("test-player-A")
    browser.find_element_by_tag_name("form").submit()

    # creating and joining new game
    WebDriverWait(browser, 5).until(
        expected_conditions.presence_of_element_located((By.CSS_SELECTOR, "div.component:nth-of-type(5)")))

    # move and resize hand area
    hand_area = browser.find_element_by_css_selector(".component:nth-of-type(5)")
    assert "test-player-A's hand" in hand_area.text
    ActionChains(browser).move_to_element(hand_area).click_and_hold().move_by_offset(0, 200).release().perform()
    assert {'left': 64, 'top': 264} == compo_pos(browser, hand_area)
    ActionChains(browser).move_to_element(hand_area).move_by_offset(hand_area.size["width"] / 2 - 1, hand_area.size[
        "height"] / 2 - 1).click_and_hold().move_by_offset(100, 30).release().perform()
    assert {'width': 422, 'height': 96} == hand_area.size


def test_put_cards_in_hand(server, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
    browser.get("http://localhost:10011/")
    # index
    browser.find_element_by_name("player").clear()
    browser.find_element_by_name("player").send_keys("test-player-A")
    browser.find_element_by_tag_name("form").submit()

    # creating and joining new game
    WebDriverWait(browser, 5).until(
        expected_conditions.presence_of_element_located((By.CSS_SELECTOR, "div.component:nth-of-type(5)")))

    hand_area = browser.find_element_by_css_selector(".component:nth-of-type(5)")
    ActionChains(browser).move_to_element(hand_area).click_and_hold().move_by_offset(0, 500).release().perform()
    hand_area_rect = rect(hand_area)
    card = browser.find_element_by_css_selector(".component:nth-of-type(3)")
    card_rect = rect(card)
    ActionChains(browser).move_to_element(card).click_and_hold().move_by_offset(
        hand_area_rect["left"] - card_rect["left"], hand_area_rect["top"] - card_rect["left"]).release().perform()

    another_browser.get(browser.current_url)
    WebDriverWait(another_browser, 5).until(
        expected_conditions.presence_of_element_located((By.CSS_SELECTOR, "div.component:nth-of-type(5)")))
    card_on_another = another_browser.find_element_by_css_selector(".component:nth-of-type(3)")
    card_pos_before_drag = compo_pos(another_browser, card_on_another)
    ActionChains(another_browser).move_to_element(card_on_another).click_and_hold().move_by_offset(50, 50).perform()
    assert card_pos_before_drag == compo_pos(another_browser, card_on_another), "not moved"
