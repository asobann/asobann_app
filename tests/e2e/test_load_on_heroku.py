import time
from threading import Thread
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from selenium.common.exceptions import NoSuchElementException

from .helper import compo_pos, Rect, GameHelper

TOP = "https://fast-dusk-61776.herokuapp.com/"


def drag_slowly(player: GameHelper, component, x, y, steps):
    for i in range(steps):
        player.drag(component, x / steps, y / steps)


saved_status = []


def save_status(iteration, tag, player: GameHelper):
    while iteration > len(saved_status) - 1:
        saved_status.append({})
    status = []
    n = 1
    while True:
        try:
            c = player.components(n, wait=False)
            status.append((c.pos(), c.size(), c.face()))
            n += 1
        except NoSuchElementException:
            break
    saved_status[iteration][tag] = status


def run_in_multithread(run_factory, number):
    threads = [Thread(target=run_factory(idx)) for idx in range(number)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def evaluate_saved_status():
    diff = 0
    for iteration in saved_status:
        baseline = iteration["host"]
        for status in [iteration[key] for key in iteration.keys() if key != "host"]:
            for i, c in enumerate(status):
                if baseline[i] != c:
                    print(f"diff! <{baseline[i]}> <{c}>")
                    diff += 1
                    break  # don't count diffs for same component
    return diff


def test_simultaneous_dragging(server, browser: webdriver.Firefox, browser_factory):
    host = GameHelper(browser)
    host.go(TOP)

    host.menu.import_jsonfile(str(Path(__file__).parent / "./test_load_on_heroku.json"))

    host.should_have_text("you are host")
    host.should_have_text("Table for load testing")

    invitation_url = host.menu.invitation_url.value

    players = []
    for i in range(8):
        player = GameHelper(browser_factory())
        player.go(invitation_url)
        player.menu.join(f"Player {i + 1}")
        player.should_have_text("Table for load testing")
        players.append(player)

    for i in range(10):
        time.sleep(1)
        save_status(i, "host", host)
        for j, p in enumerate(players):
            save_status(i, f"player{j + 1}", p)

        def run_factory(idx):
            def run():
                players[idx].drag(players[idx].components(idx + 2), 0, 300)
                players[idx].drag(players[idx].components(idx + 2), 0, -300)

            return run

        run_in_multithread(run_factory, len(players))

    assert evaluate_saved_status() == 0
