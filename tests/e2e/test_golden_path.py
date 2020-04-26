import pytest

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from selenium.common.exceptions import NoSuchElementException

def compo_pos(browser, component):
    '''
    return position of the component relative to table
    :param browser:
    :param component:
    :return: { "top": <Number>, "left": <Number> }
    '''
    table = browser.find_element_by_css_selector("div.table")
    table_loc = table.location
    comp_loc = component.location
    return { "left": comp_loc["x"] - table_loc["x"], "top": comp_loc["y"] - table_loc["y"]}


def test_golden_path(server, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
    browser.get("http://localhost:10011/")

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
    assert {'left': 150, 'top': 175} == compo_pos(browser, card)
    ActionChains(browser).move_to_element(card).move_by_offset(10, 10).click_and_hold().move_by_offset(300,
                                                                                                       50).release().perform()
    assert {'left': 450, 'top': 225} == compo_pos(browser, card)
    assert "voice_back.png" in card.find_element_by_tag_name('img').get_attribute('src')
    ActionChains(browser).double_click(card).perform()
    assert "v02.jpg" in card.find_element_by_tag_name('img').get_attribute('src')

    # open another browser and see the same cards
    another_browser.get(browser.current_url)
    WebDriverWait(another_browser, 5).until(
        expected_conditions.presence_of_element_located((By.CSS_SELECTOR, ".component:nth-of-type(3)")))
    card_on_another_browser = another_browser.find_element_by_css_selector(".component:nth-of-type(3)")
    assert {'left': 450, 'top': 225} == compo_pos(browser, card_on_another_browser)
    assert "v02.jpg" in card_on_another_browser.find_element_by_tag_name('img').get_attribute('src')


if __name__ == '__main__':
    test_golden_path()
