from selenium import webdriver
from .helper import GameHelper, TOP


def test_observers_pointer_should_not_be_seen1(server, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
    host = GameHelper(browser)
    another = GameHelper(another_browser)

    host.go(TOP)
    host.should_have_text("you are host")
    another.go(host.current_url)

    host.should_not_have_text('nobody', timeout=0.5)


def test_observers_pointer_should_not_be_seen2(server, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
    host = GameHelper(browser)
    another = GameHelper(another_browser)

    host.go(TOP)
    host.should_have_text("you are host")

    another.go(host.current_url)
    another.click(another.component_by_name('title'))
    another.move_mouse_by_offset((10, 10))

    host.should_not_have_text('nobody', timeout=0.5)


def test_observers_pointer_should_not_be_seen3(server, browser: webdriver.Firefox, browser_factory):
    host = GameHelper(browser)

    host.go(TOP)
    host.should_have_text("you are host")

    for i in range(4):
        player = GameHelper(browser_factory())
        player.go(host.current_url)
        player.click(player.component_by_name('title'))
        player.move_mouse_by_offset((10, 10))

    host.should_not_have_text('nobody', timeout=0.5)


def test_observers_pointer_should_not_be_seen4(debug_handler_wait, server, browser: webdriver.Firefox, browser_factory):
    host = GameHelper(browser)

    host.go(TOP)
    host.should_have_text("you are host")

    players = [GameHelper(browser_factory()) for i in range(4)]
    from threading import Thread

    for player in players:
        def move_mouse():
            while True:
                player.move_mouse_by_offset((30, 30))
                player.move_mouse_by_offset((-30, -30))

        def observe():
            player.go(host.current_url)

        player.move_mouse_by_offset((500, 200))
        t2 = Thread(target=observe)
        t2.start()
        Thread(target=move_mouse).start()
        t2.join()

    host.should_not_have_text('nobody', timeout=0.5)


def test_observers_pointer_should_not_be_seen5(debug_handler_wait, server, browser: webdriver.Firefox,
                                               another_browser: webdriver.Firefox):
    host = GameHelper(browser)
    another = GameHelper(another_browser)

    host.go(TOP)
    host.should_have_text("you are host")

    from threading import Thread

    def move_mouse():
        while True:
            another.move_mouse_by_offset((30, 30))
            another.move_mouse_by_offset((-30, -30))

    another.move_mouse_by_offset((500, 200))
    another.go(host.current_url)
    Thread(target=move_mouse).start()

    host.should_not_have_text('nobody', timeout=5)
