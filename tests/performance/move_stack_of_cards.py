import time
import sys
from typing import List
from multiprocessing import Queue

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
        baseline = statuses_in_iteration[0]
        for status in [statuses_in_iteration[key] for key in statuses_in_iteration.keys() if key != 0]:
            for i, c in enumerate(status):
                if baseline[i] != c:
                    log(f"diff! at {i} <{baseline[i]}> <{c}>")
                    diff += 1
                    break  # don't count diffs for same component
    return diff


def execute_controller(command_queues, result_queues, headless):
    class Group:
        def __init__(self):
            self.command_queues: List[Queue] = []
            self.result_queues: List[Queue] = []

    log('execute_controller XXX')
    groups = [Group() for i in range(int(len(command_queues) / 2))]
    workers_per_group = int(len(command_queues) / len(groups))
    log('@1', groups)
    for i, g in enumerate(groups):
        g.command_queues = [command_queues.pop() for j in range(workers_per_group)]
        g.result_queues = [result_queues.pop() for j in range(workers_per_group)]

    log('@2')
    for group in groups:
        group.command_queues[0].put(['create empty table'])
        url = group.result_queues[0].get()
        for q in group.command_queues[1:]:
            q.put(['open', url])

    log('@3')
    for i in range(10):
        for group in groups:
            group.command_queues[0].put(['move'])
        for group in groups:
            group.result_queues[0].get()

    log('@4')
    for group in groups:
        for q in group.command_queues:
            q.put(['status'])
        for i, q in enumerate(group.result_queues):
            save_status(0, i, q.get())

    log('@5')
    for group in groups:
        for q in group.command_queues:
            q.put(['finish'])

    return evaluate_saved_status()

    try:
        log('execute move_stack_of_cards controller')
        host = GameHelper(window, base_url=STAGING_TOP)
        host.create_table(0)

        host.should_have_text("you are host")
        host.menu.add_kit.execute()
        host.menu.add_kit_from_list("Playing Card")

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

    finally:
        window.close()


def execute_worker(name, command_queue, result_queue, headless):
    window = browser(headless=headless)
    try:
        player = GameHelper(window, base_url=STAGING_TOP)

        imagecount = 0
        log('entering loop')
        while True:
            cmd = command_queue.get()
            log(f'received command {cmd}')
            if cmd[0] == 'create empty table':
                player.create_table(0)
                player.should_have_text("you are host")
                player.menu.add_kit.execute()
                player.menu.add_kit_from_list("Playing Card")
                result_queue.put(player.current_url)
            elif cmd[0] == 'open':
                player.go(cmd[1])
            elif cmd[0] == 'move':
                player.drag(player.component_by_name("Playing Card Box"), 200, 100, grab_at=(0, 48))
                time.sleep(0.1)  # avoid double clicking
                player.drag(player.component_by_name("Playing Card Box"), -200, -100, grab_at=(0, 48))
                result_queue.put('moved')
            elif cmd[0] == 'status':
                player.browser.save_screenshot(f'/runner/image{imagecount}.png')
                imagecount += 1
                result_queue.put(gather_status(player))
            elif cmd[0] == 'finish':
                return
            else:
                raise RuntimeError(f'unknown command {cmd}')
            log('continue ...')

    finally:
        window.close()
