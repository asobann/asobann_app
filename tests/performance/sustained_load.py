"""
Step 2/3/4 of the slowness-repro plan: reproduce "gets slow after several people use it
for tens of minutes" by keeping every player generating realistic mousemove load (the
suspected N^2 broadcast amplification path - see issues.fable5.20260706.md #2) plus
occasional card drags, continuously for `duration_seconds`, while measuring mousemove
delivery latency between every pair of players at `report_interval_seconds` cadence.

Parameters (pass via `--param key=value`, see cli.py):
  duration_seconds        total load duration (default 180)
  mousemove_hz            per-player synthetic mousemove send rate (default 30)
  drag_interval_seconds   seconds between each worker's card drags (default 10)
  report_interval_seconds seconds between latency measurement snapshots (default 60)

Output: {'timeline': [{'elapsed_seconds': int, 'pairs': [...], 'drag_seconds': {...}}, ...]}
`pairs` is mouse_latency.evaluate_all_pairs' output for that interval: one entry per
(sender, receiver) with sent/received counts, loss_rate, and p50/p95/max latency in ms.
A widening p95/loss_rate over the timeline is the signature of the slowness this test
is trying to reproduce.

Run: python -m tests.performance.cli run tests.performance.sustained_load <N> \
    --run-on docker --url https://staging.asobann.yattom.jp \
    --param duration_seconds=180 --param mousemove_hz=30 --output results/smoke.json
"""

import sys
import time
from pathlib import Path

from ..e2e.conftest import browser_func as browser
from ..e2e.helper import GameHelper, STAGING_TOP
from .mouse_latency import evaluate_all_pairs_timeseries

KIT_FILE = Path(__file__).parent / "sustained_load.json"

# Raised on the controller's side of a result_queue.get() when that worker's own
# manager connection has already gone away (e.g. its browser crashed and it called
# mgr.shutdown() on itself - see remote_runner.py's worker exception handling).
WORKER_DISCONNECT_ERRORS = (EOFError, ConnectionError, BrokenPipeError)

DEFAULTS = {
    'duration_seconds': 180,
    'mousemove_hz': 30,
    'drag_interval_seconds': 10,
    'report_interval_seconds': 60,
}


def log(*args):
    print(*args)
    sys.stdout.flush()


def get_params(parameters):
    return {key: int(parameters.get(key, default)) for key, default in DEFAULTS.items()}


def execute_controller(command_queues, result_queues, parameters):
    headless = parameters['headless']
    url = parameters['url'] if 'url' in parameters else STAGING_TOP
    p = get_params(parameters)
    cycles = max(1, round(p['duration_seconds'] / p['report_interval_seconds']))
    log(f'execute sustained_load controller: {p}, cycles={cycles}')

    window = browser(headless=headless)
    try:
        host = GameHelper(window, base_url=url)
        host.go(url)
        host.menu.import_jsonfile(str(KIT_FILE))
        host.should_have_text("you are host")
        host.should_have_text("Table for sustained load testing")
        invitation_url = host.menu.invitation_url.value
        log(f'table is opened at {invitation_url}')

        host.start_mouse_load(hz=p['mousemove_hz'])
        host.start_mouse_receive_observer()
        start_at_ms = now_ms()

        for idx, q in enumerate(command_queues):
            q.put([idx, invitation_url])

        # Accumulate the whole run's sent/received data per player rather than pairing
        # each report interval's drained chunk in isolation - see mouse_latency.
        # evaluate_all_pairs_timeseries for why per-interval-only pairing undercounts
        # messages that cross a drain boundary.
        sent_by_player = {'host': []}
        received_by_receiver = {'host': {}}
        drag_seconds_by_worker = {}
        dead_workers = set()  # a browser crash in one worker must not lose every other
                              # worker's data for the whole run - see WORKER_DISCONNECT_ERRORS

        for cycle in range(cycles):
            time.sleep(p['report_interval_seconds'])

            sent_by_player['host'] += host.collect_and_clear_mouse_send_log()
            merge_received(received_by_receiver['host'], host.collect_and_clear_mouse_receive_log())

            for idx, q in enumerate(result_queues):
                if idx in dead_workers:
                    continue
                worker_name = f'P{idx}'
                try:
                    r = q.get()
                except WORKER_DISCONNECT_ERRORS as ex:
                    log(f'{worker_name} appears to have crashed ({ex!r}); '
                        f'continuing the run with the remaining workers')
                    dead_workers.add(idx)
                    continue
                sent_by_player.setdefault(worker_name, [])
                sent_by_player[worker_name] += r['sent']
                received_by_receiver.setdefault(worker_name, {})
                merge_received(received_by_receiver[worker_name], r['received'])
                drag_seconds_by_worker.setdefault(worker_name, []).extend(r['drag_seconds'])

            log(f'cycle {cycle + 1}/{cycles} (elapsed {(cycle + 1) * p["report_interval_seconds"]}s) collected, '
                f'{len(dead_workers)} dead worker(s)')

        host.stop_mouse_load()
        for idx, q in enumerate(result_queues):
            if idx in dead_workers:
                continue
            try:
                q.get()  # final {'finished': True} marker
            except WORKER_DISCONNECT_ERRORS:
                pass

        buckets = evaluate_all_pairs_timeseries(
            sent_by_player, received_by_receiver, start_at_ms, p['report_interval_seconds'])
        timeline = [
            {'elapsed_seconds': (bucket_idx + 1) * p['report_interval_seconds'], 'pairs': buckets[bucket_idx]}
            for bucket_idx in sorted(buckets.keys())
            if bucket_idx >= 0  # drop the handful of host ticks sent before start_at_ms was captured
        ]

        return {
            'params': p,
            'timeline': timeline,
            'drag_seconds_by_worker': drag_seconds_by_worker,
        }
    finally:
        window.close()


def now_ms():
    return int(time.time() * 1000)


def merge_received(target: dict, addition: dict):
    for player_name, observations in addition.items():
        target.setdefault(player_name, [])
        target[player_name] += observations


def execute_worker(name, command_queue, result_queue, parameters):
    headless = parameters['headless']
    p = get_params(parameters)
    cycles = max(1, round(p['duration_seconds'] / p['report_interval_seconds']))
    drags_per_cycle = max(1, round(p['report_interval_seconds'] / p['drag_interval_seconds']))

    window = browser(headless=headless)
    try:
        player = GameHelper(window)
        idx, invitation_url = command_queue.get()
        player.go(invitation_url)
        player.menu.join(f'P{idx}')
        player.should_have_text(f"you are P{idx}")
        nth = idx + 2  # component(1) is the NOTE; cards start at 2, see sustained_load.json

        player.start_mouse_load(hz=p['mousemove_hz'])
        player.start_mouse_receive_observer()

        for cycle in range(cycles):
            drag_seconds = []
            for _ in range(drags_per_cycle):
                time.sleep(p['drag_interval_seconds'])
                started_at = time.monotonic()
                player.drag(player.component(nth), 0, 100)
                time.sleep(0.1)  # avoid double clicking, matches other scenarios
                player.drag(player.component(nth), 0, -100)
                drag_seconds.append(time.monotonic() - started_at)

            result_queue.put({
                'sent': player.collect_and_clear_mouse_send_log(),
                'received': player.collect_and_clear_mouse_receive_log(),
                'drag_seconds': drag_seconds,
            })
            log(f'{name}: cycle {cycle + 1}/{cycles} reported')

        player.stop_mouse_load()
        result_queue.put({'finished': True})
    finally:
        window.close()
