import time
from threading import Thread
from pathlib import Path

from selenium.common.exceptions import NoSuchElementException, TimeoutException

from ..e2e.conftest import browser as browser_fixture
from ..e2e.helper import compo_pos, Rect, GameHelper, STAGING_TOP


def browser():
    return next(browser_fixture())


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
            status.append((c.pos(), c.size(), c.face()))
            n += 1
        except NoSuchElementException:
            break
    return status


def save_status(iteration, tag, player: GameHelper):
    while iteration > len(saved_status) - 1:
        saved_status.append({})
    status = gather_status(player)
    saved_status[iteration][tag] = status


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


def simultaneous_dragging_controller(cmd_queues, result_queues):
    for q in cmd_queues:
        q.put('run simultaneous_dragging_worker')

    host = GameHelper(browser())
    host.go(STAGING_TOP)

    host.menu.import_jsonfile(str(Path(__file__).parent / "./test_load_on_heroku.json"))

    host.should_have_text("you are host")
    host.should_have_text("Table for load testing")

    invitation_url = host.menu.invitation_url.value

    for idx, q in enumerate(cmd_queues):
        q.put(idx, invitation_url)

    for i in range(10):
        time.sleep(1)
        save_status(i, "host", host)
        for j, q in enumerate(result_queues):
            save_status(i, f"player{j + 1}", q.get())
        for q in cmd_queues:
            q.put('move')

    for q in cmd_queues:
        q.put('finish')

    assert evaluate_saved_status() == 0


def simultaneous_dragging_worker(name, cmd_queue, result_queue):
    player = GameHelper(browser())
    my_idx, invitation_url = cmd_queue.get()
    player.go(invitation_url)
    player.menu.join(name)
    player.should_have_text("Table for load testing")

    while True:
        cmd = cmd_queue.get()
        if cmd == 'move':
            player.drag(player.component(my_idx + 2), 0, 300)
            time.sleep(0.1)  # avoid double clicking
            player.drag(player.component(my_idx + 2), 0, -300)
        elif cmd == 'status':
            result_queue.put(gather_status(player))
        elif cmd == 'finish':
            break
        else:
            raise RuntimeError(f'unknown command {cmd}')
