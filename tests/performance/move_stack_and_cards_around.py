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
    iteration = 10
    workers_per_group = 8

    class Group:
        def __init__(self):
            self.command_queues: List[Queue] = []
            self.result_queues: List[Queue] = []

    groups = [Group() for i in range(int(len(command_queues) / workers_per_group))]
    cq, rq = command_queues[:], result_queues[:]
    for i, g in enumerate(groups):
        g.command_queues = [cq.pop() for j in range(workers_per_group)]
        g.result_queues = [rq.pop() for j in range(workers_per_group)]

        g.stack_mover = (g.command_queues[0], g.result_queues[0])
        g.card_movers = (g.command_queues[1:], g.result_queues[1:])

    log('execute_controller')

    for g in groups:
        g.stack_mover[0].put(['create empty table'])
        url = g.stack_mover[1].get()

        for i, q in enumerate(g.card_movers[0]):
            q.put(['idx', i])
            q.put(['open', url])
            q.put(['grab card'])
            log('grabbed: ' + g.card_movers[1][i].get())  # grabbed

    for g in groups:
        for i in range(iteration):
            g.stack_mover[0].put(['move stack'])
            for q in g.card_movers[0]:
                q.put(['move card', i])

    for g in groups:
        for q in g.command_queues:
            q.put(['echo back'])
        for q in g.result_queues:
            q.get()  # echo back

        for q in g.command_queues:
            q.put(['status'])
        for tag, q in enumerate(g.result_queues):
            save_status(0, tag, q.get())

    command_queues[-1].put(['screen utilization'])
    utilization = result_queues[-1].get()

    for q in command_queues:
        q.put(['finish'])

    diff_count = evaluate_saved_status()
    return {
        'diff_count': diff_count,
        'workers': len(command_queues),
        'worker_groups': len(groups),
        'iteration': iteration,
        'screen utilization': utilization,
        # 'saved_status': saved_status,
    }


def execute_worker(name, command_queue, result_queue, headless):
    window = browser(headless=headless)
    try:
        my_idx = -1
        nth = -1
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
            elif cmd[0] == 'idx':
                my_idx = cmd[1]
            elif cmd[0] == 'open':
                player.go(cmd[1])
                player.menu.join(f'P{my_idx}')
                player.should_have_text(f"you are P{my_idx}")
            elif cmd[0] == 'grab card':
                nth = my_idx + 2
                log(my_idx, player.component(nth).name)
                player.drag(player.component(nth), -120 + 80 * my_idx, 300)
                result_queue.put('grabbed')
            elif cmd[0] == 'move stack':
                player.drag(player.component_by_name("Playing Card Box"), 40, 0, grab_at=(0, 48))
                time.sleep(0.1)  # avoid double clicking
                player.drag(player.component_by_name("Playing Card Box"), -40, 0, grab_at=(0, 48))
            elif cmd[0] == 'move card':
                player.drag(player.component(nth), 0, 200)
                time.sleep(0.1)  # avoid double clicking
                player.drag(player.component(nth), 0, -200)
            elif cmd[0] == 'status':
                player.browser.save_screenshot(f'/runner/image{imagecount}.png')
                imagecount += 1
                result_queue.put(gather_status(player))
            elif cmd[0] == 'echo back':
                result_queue.put('echo back')
            elif cmd[0] == 'screen utilization':
                result_queue.put(get_screen_utilization(player))
            elif cmd[0] == 'finish':
                return
            else:
                raise RuntimeError(f'unknown command {cmd}')
            log('continue ...')

    finally:
        window.close()


def get_screen_utilization(game_helper):
    left = top = 9999
    right = bottom = 0
    component_statuses = gather_status(game_helper)
    for rect, face in component_statuses:
        if rect.left < left:
            left = rect.left
        if rect.top < top:
            top = rect.top
        if right < rect.right:
            right = rect.right
        if bottom < rect.bottom:
            bottom = rect.bottom

    utilization = {
        'screen size': game_helper.browser.get_window_size(),
        'component uses': {
            'left': left,
            'top': top,
            'right': right,
            'bottom': bottom,
        },
        'component count': len(component_statuses),
    }
    return utilization
