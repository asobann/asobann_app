from selenium import webdriver
from .helper import GameHelper, TOP


def test_observers_pointer_should_not_be_seen(debug_handler_wait, server, browser: webdriver.Firefox,
                                               another_browser: webdriver.Firefox):
    host = GameHelper(browser)
    another = GameHelper(another_browser)

    host.go(TOP)
    host.should_have_text("you are host")

    from threading import Thread
    running = True

    def move_mouse():
        while running:
            another.move_mouse_by_offset((30, 30))
            another.move_mouse_by_offset((-30, -30))

    another.move_mouse_by_offset((500, 200))
    another.go(host.current_url)
    thread = Thread(target=move_mouse)
    thread.start()

    host.should_not_have_text('nobody', timeout=5)

    running = False
    thread.join()
