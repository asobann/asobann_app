from selenium import webdriver
from .helper import GameHelper, TOP


def move_mouse(helper: GameHelper):
    helper.move_mouse_by_offset((500, 200))
    helper.move_mouse_by_offset((30, 30))
    helper.move_mouse_by_offset((-30, -30))



def test_observers_pointer_should_not_be_seen(debug_handler_wait, server, browser: webdriver.Firefox,
                                               another_browser: webdriver.Firefox):
    host = GameHelper(browser)
    another = GameHelper(another_browser)

    host.go(TOP)
    host.should_have_text("you are host")

    another.go(host.current_url)
    move_mouse(another)

    host.should_not_have_text('nobody', timeout=5)


def test_other_players_pointer_should_be_seen(debug_handler_wait, server, browser: webdriver.Firefox,
                                               another_browser: webdriver.Firefox):
    host = GameHelper(browser)
    another = GameHelper(another_browser)

    host.go(TOP)
    host.should_have_text("you are host")

    another.go(host.current_url)
    another.menu.join("Player 2")
    move_mouse(another)

    host.should_have_text('Player 2')
