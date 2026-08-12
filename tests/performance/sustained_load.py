"""
Reproduce "gets slow after several people use it for tens of minutes" (issue #134) by
keeping every player generating realistic mousemove load plus occasional card drags,
continuously for `duration_seconds`, while measuring mousemove delivery latency between
every pair of players at `report_interval_seconds` cadence.

The suspected mechanism is the N^2 broadcast amplification path: the server re-emits each
received mousemove to the whole room, so fanout stays N-1 per message. Measured CPU cost,
however, came out closer to linear in players x Hz for 2-6 players, which suggests the
per-received-message handling dominates over the fanout itself. That does not rule out the
N^2 path at higher player counts - saturation at 6 players made it unmeasurable.

Parameters (pass via `--param key=value`, see cli.py):
  duration_seconds        total load duration (default 180)
  mousemove_hz            per-player synthetic mousemove send rate (default 30)
  drag_interval_seconds   seconds between each worker's card operations (default 10; 0 disables them)
  operation               'drag' (default), 'flip', or 'pause_only'. drag/flip both go
                          through the mongo-write + broadcast path; flip never moves the
                          card, so it cannot fail by the card drifting out of the
                          viewport. pause_only does no component operation at all - see
                          its comment in execute_worker for what it isolates.
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
from ..support.mouse_latency import evaluate_all_pairs_timeseries

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

        # hz=0 means "idle": a baseline config that keeps players connected without
        # generating any mousemove load. JS's setInterval(fn, 1000/0) is Infinity, which
        # is unreliable across browsers, so skip starting the load entirely rather than
        # relying on it never firing.
        if p['mousemove_hz'] > 0:
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
        flips_not_applied_by_worker = {}
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
                if 'sent' not in r:
                    # worker_server's outer except caught an exception raised inside
                    # execute_worker (e.g. a Selenium call failing mid-drag) and put an
                    # {'error': {...}} dict instead of a per-cycle report, then shut itself
                    # down - the queue read itself succeeds, so this isn't caught above.
                    log(f'{worker_name} reported an error and is shutting down: '
                        f'{r.get("error", r)!r}; continuing the run with the remaining workers')
                    dead_workers.add(idx)
                    continue
                sent_by_player.setdefault(worker_name, [])
                sent_by_player[worker_name] += r['sent']
                received_by_receiver.setdefault(worker_name, {})
                merge_received(received_by_receiver[worker_name], r['received'])
                drag_seconds_by_worker.setdefault(worker_name, []).extend(r['drag_seconds'])
                flips_not_applied_by_worker[worker_name] = r.get('flips_not_applied', 0)

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
            'flips_not_applied_by_worker': flips_not_applied_by_worker,
        }
    finally:
        window.close()


def describe_card(player, card_name):
    """
    Report where the card actually is when an operation fails on it. A TimeoutException
    from component_by_name() only says "not visible within 5s", which does not distinguish
    "gone from the DOM" from "still there but scrolled far out of view" - the latter is
    what an earlier coordinate bug produced (y ~ -96000).
    """
    try:
        return player.browser.execute_script(
            """
            const el = document.querySelector(
                `.component[data-component-name='` + arguments[0] + `']`);
            if (!el) { return 'card is absent from the DOM'; }
            const r = el.getBoundingClientRect();
            const s = getComputedStyle(el);
            return `card at (${Math.round(r.x)},${Math.round(r.y)}) size ${Math.round(r.width)}x${Math.round(r.height)} `
                 + `display=${s.display} visibility=${s.visibility} opacity=${s.opacity}`;
            """,
            card_name)
    except Exception as ex:
        return f'could not inspect card: {ex!r}'


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
    # drag_interval_seconds == 0 disables drags entirely, leaving pure mousemove load.
    # Useful to isolate the broadcast path from the mongo-write path ('update many
    # components' persists on every drag event), and it also sidesteps the worker
    # crashes observed mid-drag under load.
    if p['drag_interval_seconds'] > 0:
        drags_per_cycle = max(1, round(p['report_interval_seconds'] / p['drag_interval_seconds']))
    else:
        drags_per_cycle = 0

    window = browser(headless=headless)
    try:
        player = GameHelper(window)
        idx, invitation_url = command_queue.get()
        player.go(invitation_url)
        player.menu.join(f'P{idx}')
        player.should_have_text(f"you are P{idx}")
        # Address the card by its data-component-name, the way the e2e tests do, rather
        # than by DOM position: component(nth) resolves `.component:nth-of-type(N)`, and
        # once several players start dragging cards around, the element at position N is
        # no longer the card this worker owns (it can also stop matching entirely, which
        # made every worker die on a TimeoutException within ~2 minutes of a drag-enabled run).
        my_card_name = f'card{idx + 1}'  # see sustained_load.json
        operation = parameters.get('operation', 'drag')
        flips_not_applied = 0  # flips where the face did not change (operation lost)

        if p['mousemove_hz'] > 0:
            player.start_mouse_load(hz=p['mousemove_hz'])
        player.start_mouse_receive_observer()

        for cycle in range(cycles):
            drag_seconds = []
            if drags_per_cycle == 0:
                time.sleep(p['report_interval_seconds'])
            for _ in range(drags_per_cycle):
                time.sleep(p['drag_interval_seconds'])
                started_at = time.monotonic()
                # Pause the ambient cursor motion while operating a component: a real
                # player's pointer cannot be waving around and dragging at the same time,
                # and running both at once sent cards to y = -96000px until they left the
                # viewport (see pause_mouse_load).
                player.pause_mouse_load()
                try:
                    if operation == 'pause_only':
                        # No component operation at all - same pause/resume cadence as
                        # 'flip' (including the settle sleep) but no server request.
                        # Isolates how much of flip's lower CPU (vs mouseonly) comes from
                        # the ambient mousemove being paused during each operation, versus
                        # the cost of the flip request itself.
                        time.sleep(0.3)
                    elif operation == 'flip':
                        # Flipping never moves the component, so it cannot fail by the card
                        # drifting out of the viewport - but it still goes through the same
                        # 'update single component' path (mongo write + broadcast).
                        # sustained_load.json gives every card faceupText/facedownText, so
                        # the face itself tells us whether the operation actually landed
                        # rather than merely not raising.
                        before = player.component_by_name(my_card_name).face()
                        player.double_click(player.component_by_name(my_card_name))
                        time.sleep(0.3)  # let the flip round-trip through the server
                        after = player.component_by_name(my_card_name).face()
                        if before == after:
                            flips_not_applied += 1
                    else:
                        player.drag(player.component_by_name(my_card_name), 0, 100)
                        time.sleep(0.1)  # avoid double clicking, matches other scenarios
                        player.drag(player.component_by_name(my_card_name), 0, -100)
                except Exception:
                    log(f'{name}: {operation} failed; {describe_card(player, my_card_name)}')
                    raise
                finally:
                    time.sleep(0.2)  # let the operation's own events drain before resuming
                    player.resume_mouse_load(hz=p['mousemove_hz'])
                drag_seconds.append(time.monotonic() - started_at)

            result_queue.put({
                'sent': player.collect_and_clear_mouse_send_log(),
                'received': player.collect_and_clear_mouse_receive_log(),
                'drag_seconds': drag_seconds,
                'flips_not_applied': flips_not_applied,
            })
            log(f'{name}: cycle {cycle + 1}/{cycles} reported')

        player.stop_mouse_load()
        result_queue.put({'finished': True})
    finally:
        window.close()
