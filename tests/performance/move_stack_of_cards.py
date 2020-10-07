import time
import sys
from typing import List
from multiprocessing import Queue

from pathlib import Path

from ..e2e.conftest import browser_func as browser
from ..e2e.helper import compo_pos, Rect, GameHelper, STAGING_TOP
from . import status_diff


def log(*args):
    print(*args)
    sys.stdout.flush()


def drag_slowly(player: GameHelper, component, x, y, steps):
    for i in range(steps):
        player.drag(component, x / steps, y / steps)


def execute_controller(command_queues, result_queues, parameters):
    headless = parameters['headless']
    url = parameters['url'] if 'url' in parameters else STAGING_TOP
    iteration = 10

    class Group:
        def __init__(self):
            self.command_queues: List[Queue] = []
            self.result_queues: List[Queue] = []

    log('execute_controller')
    groups = [Group() for i in range(int(len(command_queues) / 2))]
    workers_per_group = int(len(command_queues) / len(groups))
    cq, rq = command_queues[:], result_queues[:]
    for i, g in enumerate(groups):
        g.command_queues = [cq.pop() for j in range(workers_per_group)]
        g.result_queues = [rq.pop() for j in range(workers_per_group)]

    for group in groups:
        group.command_queues[0].put(['create empty table'])
        url = group.result_queues[0].get()
        for q in group.command_queues[1:]:
            q.put(['open', url])

    for i in range(iteration):
        for group in groups:
            group.command_queues[0].put(['move'])
        for group in groups:
            group.result_queues[0].get()

        for group in groups:
            for q in group.command_queues:
                q.put(['status'])
            for tag, q in enumerate(group.result_queues):
                status_diff.save_status(i, tag, q.get())

    for group in groups:
        for q in group.command_queues:
            q.put(['finish'])

    diff = status_diff.evaluate_saved_status()
    return {
        'diff': diff,
        'worker_groups': len(groups),
        'iteration': iteration,
        # 'saved_status': saved_status,
    }


def execute_worker(name, command_queue, result_queue, parameters):
    headless = parameters['headless']
    url = parameters['url'] if 'url' in parameters else STAGING_TOP
    window = browser(headless=headless)
    try:
        player = GameHelper(window, base_url=url)

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
                result_queue.put(status_diff.gather_status(player))
            elif cmd[0] == 'finish':
                return
            else:
                raise RuntimeError(f'unknown command {cmd}')
            log('continue ...')

    finally:
        window.close()
