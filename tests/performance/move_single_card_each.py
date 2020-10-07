import time
import sys
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
    log('execute move_single_card_each controller')
    window = browser(headless=headless)
    try:
        host = GameHelper(window, base_url=url)
        host.go(url)

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
            status_diff.save_status(i, "host", status_diff.gather_status(host))
            log('receive status')
            for q in command_queues:
                q.put('status')
            for j, q in enumerate(result_queues):
                status_diff.save_status(i, f"player{j + 1}", q.get())
            log('continue ...')

        log('finishing up ...')
        for q in command_queues:
            q.put('finish')

        return status_diff.evaluate_saved_status(baseline_key='host')
    finally:
        window.close()


def execute_worker(name, command_queue, result_queue, parameters):
    headless = parameters['headless']
    url = parameters['url'] if 'url' in parameters else STAGING_TOP
    window = browser(headless=headless)
    try:
        player = GameHelper(window, base_url=url)
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
                result_queue.put(status_diff.gather_status(player))
            elif cmd == 'finish':
                break
            else:
                raise RuntimeError(f'unknown command {cmd}')
            log('continue ...')
    finally:
        window.close()
