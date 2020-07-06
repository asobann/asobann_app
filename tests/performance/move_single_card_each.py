import time
import sys
from pathlib import Path

from selenium.common.exceptions import NoSuchElementException, TimeoutException

from ..e2e.conftest import browser_func as browser
from ..e2e.helper import compo_pos, Rect, GameHelper, STAGING_TOP


def log(*args):
    print(*args)
    sys.stdout.flush()


def drag_slowly(player: GameHelper, component, x, y, steps):
    for i in range(steps):
        player.drag(component, x / steps, y / steps)


saved_status = []


def gather_status(player: GameHelper):
    status = []
    n = 1
    while True:
        try:
            c = player.component(n, wait=False)
            status.append((c.rect(), c.face()))
            n += 1
        except NoSuchElementException:
            break
    return status


def save_status(iteration, tag, status: list):
    while iteration > len(saved_status) - 1:
        saved_status.append({})
    saved_status[iteration][tag] = status


def evaluate_saved_status():
    diff = 0
    for statuses_in_iteration in saved_status:
        baseline = statuses_in_iteration["host"]
        for status in [statuses_in_iteration[key] for key in statuses_in_iteration.keys() if key != "host"]:
            for i, c in enumerate(status):
                if baseline[i] != c:
                    log(f"diff! at {i} <{baseline[i]}> <{c}>")
                    diff += 1
                    break  # don't count diffs for same component
    return diff


def execute_controller(command_queues, result_queues):
    log('execute move_single_card_each controller')
    host = GameHelper(browser(headless=True))
    host.go(STAGING_TOP)

    host.menu.import_jsonfile(str(Path(__file__).parent / "./move_single_card_each.json"))

    host.should_have_text("you are host")
    host.should_have_text("Table for load testing")

    invitation_url = host.menu.invitation_url.value
    log(f'table is opened at {invitation_url}')

    for idx, q in enumerate(command_queues):
        q.put([idx, invitation_url])

    log('loop 10 times')
    for i in range(10):
        log(i)
        log('move')
        for q in command_queues:
            q.put('move')
        for q in result_queues:
            q.get()  # 'moved'
        time.sleep(3)
        save_status(i, "host", gather_status(host))
        log('receive status')
        for q in command_queues:
            q.put('status')
        for j, q in enumerate(result_queues):
            save_status(i, f"player{j + 1}", q.get())
        log('continue ...')

    log('finishing up ...')
    for q in command_queues:
        q.put('finish')

    return evaluate_saved_status()


def execute_worker(name, command_queue, result_queue):
    player = GameHelper(browser(headless=True))
    my_idx, invitation_url = command_queue.get()
    player.go(invitation_url)
    player.menu.join(f'P{my_idx}')
    player.should_have_text("Table for load testing")

    imagecount = 0
    log('entering loop')
    while True:
        cmd = command_queue.get()
        log(f'received command {cmd}')
        if cmd == 'move':
            player.drag(player.component(my_idx + 2), 0, 300)
            time.sleep(0.1)  # avoid double clicking
            player.drag(player.component(my_idx + 2), 0, -300)
            result_queue.put('moved')
        elif cmd == 'status':
            player.browser.save_screenshot(f'/runner/image{imagecount}.png')
            imagecount += 1
            result_queue.put(gather_status(player))
        elif cmd == 'finish':
            break
        else:
            raise RuntimeError(f'unknown command {cmd}')
        log('continue ...')
