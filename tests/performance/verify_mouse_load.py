"""
Step 1 verification for the slowness-repro plan (see plan.slowness-repro-test.*.md):
confirms that GameHelper.start_mouse_load's synthetic mousemove events actually reach
another player's screen through the real app path (mousemove listener -> socket.emit
-> server broadcast -> socket.on -> showOthersMouseMovement), and that the pairing in
mouse_latency.py produces sane latencies.

Run: python -m tests.performance.cli run tests.performance.verify_mouse_load 1 \
    --run-on docker --url https://staging.asobann.yattom.jp --debug
"""

import sys
import time

from ..e2e.conftest import browser_func as browser
from ..e2e.helper import GameHelper, STAGING_TOP
from .mouse_latency import evaluate_pair

HZ = 30
LOAD_SECONDS = 10


def log(*args):
    print(*args)
    sys.stdout.flush()


def execute_controller(command_queues, result_queues, parameters):
    headless = parameters['headless']
    url = parameters['url'] if 'url' in parameters else STAGING_TOP
    log('execute verify_mouse_load controller')
    window = browser(headless=headless)
    try:
        host = GameHelper(window, base_url=url)
        host.go(url)
        host.should_have_text("you are host")
        invitation_url = host.menu.invitation_url.value
        log(f'table is opened at {invitation_url}')

        host.start_mouse_receive_observer()

        for q in command_queues:
            q.put(['open', invitation_url])
        for q in result_queues:
            assert q.get() == 'joined'

        for q in command_queues:
            q.put(['load', HZ, LOAD_SECONDS])

        # let the load run; poll observed positions a few times while it's happening
        for _ in range(LOAD_SECONDS):
            time.sleep(1)

        worker_names = []
        for q in command_queues:
            q.put(['finish'])
        for q in result_queues:
            name, sent = q.get()
            worker_names.append((name, sent))

        received = host.collect_and_clear_mouse_receive_log()

        results = []
        for name, sent in worker_names:
            observed = received.get(name, [])
            results.append(evaluate_pair(name, 'host', sent['sent'], observed))

        return {'results': results}
    finally:
        window.close()


def execute_worker(name, command_queue, result_queue, parameters):
    headless = parameters['headless']
    window = browser(headless=headless)
    try:
        player = GameHelper(window)
        while True:
            cmd = command_queue.get()
            log(f'received command {cmd}')
            if cmd[0] == 'open':
                player.go(cmd[1])
                player.menu.join(name)
                player.should_have_text(f"you are {name}")
                result_queue.put('joined')
            elif cmd[0] == 'load':
                hz, seconds = cmd[1], cmd[2]
                player.start_mouse_load(hz=hz)
                time.sleep(seconds)
            elif cmd[0] == 'finish':
                sent = player.stop_mouse_load()
                result_queue.put((name, sent))
                return
            else:
                raise RuntimeError(f'unknown command {cmd}')
    finally:
        window.close()
