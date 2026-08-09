"""
Debug scenario for the drag failure seen in sustained_load: every worker dies with a
TimeoutException on component_by_name() a minute or two into a drag-enabled run, even
though the same load without drags stays healthy for 30 minutes.

Captures a screenshot plus a DOM dump at the moment the lookup fails (and one just before
the first drag, for comparison), so we can see what actually happened to the card.

Screenshots are written inside the worker container under /runner/debug_out/ and copied
out by the caller (see the docker cp in the accompanying shell commands).

Run: python -m tests.performance.cli run tests.performance.debug_drag_failure 3 \
    --run-on docker --url https://staging.asobann.yattom.jp --param mousemove_hz=30
"""

import sys
import time
import traceback
from pathlib import Path

from ..e2e.conftest import browser_func as browser
from ..e2e.helper import GameHelper, STAGING_TOP

KIT_FILE = Path(__file__).parent / "sustained_load.json"
OUT_DIR = Path('/runner/debug_out')


def log(*args):
    print(*args)
    sys.stdout.flush()


def dump_state(player: GameHelper, tag: str):
    OUT_DIR.mkdir(exist_ok=True)
    try:
        player.browser.save_screenshot(str(OUT_DIR / f'{tag}.png'))
    except Exception as ex:
        log(f'screenshot failed for {tag}: {ex!r}')
    try:
        info = player.browser.execute_script(
            """
            const comps = Array.from(document.querySelectorAll('.component')).map((el) => ({
                name: el.getAttribute('data-component-name'),
                display: getComputedStyle(el).display,
                visibility: getComputedStyle(el).visibility,
                opacity: getComputedStyle(el).opacity,
                rect: el.getBoundingClientRect(),
                style: el.getAttribute('style'),
            }));
            return {
                url: location.href,
                bodyTextHead: document.body ? document.body.innerText.slice(0, 400) : null,
                componentCount: comps.length,
                components: comps,
            };
            """
        )
        with open(OUT_DIR / f'{tag}.json', 'w') as f:
            import json
            json.dump(info, f, indent=2, default=str)
        log(f'[{tag}] url={info["url"]} componentCount={info["componentCount"]} '
            f'names={[c["name"] for c in info["components"]]}')
    except Exception as ex:
        log(f'dom dump failed for {tag}: {ex!r}')


def execute_controller(command_queues, result_queues, parameters):
    headless = parameters['headless']
    url = parameters['url'] if 'url' in parameters else STAGING_TOP
    hz = int(parameters.get('mousemove_hz', 30))
    window = browser(headless=headless)
    try:
        host = GameHelper(window, base_url=url)
        host.go(url)
        host.menu.import_jsonfile(str(KIT_FILE))
        host.should_have_text("you are host")
        host.should_have_text("Table for sustained load testing")
        invitation_url = host.menu.invitation_url.value
        log(f'table at {invitation_url}')

        host.start_mouse_load(hz=hz)

        for idx, q in enumerate(command_queues):
            q.put([idx, invitation_url])

        results = []
        for q in result_queues:
            results.append(q.get())
        return {'workers': results}
    finally:
        window.close()


def execute_worker(name, command_queue, result_queue, parameters):
    headless = parameters['headless']
    hz = int(parameters.get('mousemove_hz', 30))
    window = browser(headless=headless)
    try:
        player = GameHelper(window)
        idx, invitation_url = command_queue.get()
        player.go(invitation_url)
        player.menu.join(f'P{idx}')
        player.should_have_text(f"you are P{idx}")
        my_card_name = f'card{idx + 1}'

        player.start_mouse_load(hz=hz)
        if parameters.get('with_observer', 'false') in (True, 'true'):
            # The one thing sustained_load does that this scenario originally didn't.
            # Suspected of saturating the browser's main thread (it observes every style
            # mutation under div.table, which under load is 90+/s of cursor moves plus
            # every dragged component), starving Selenium's element lookups.
            player.start_mouse_receive_observer()
            log(f'P{idx}: mouse receive observer ENABLED')
        else:
            log(f'P{idx}: mouse receive observer disabled')

        dump_state(player, f'P{idx}_00_before_any_drag')

        collect = parameters.get('with_collect', 'false') in (True, 'true')
        log(f'P{idx}: periodic log collection {"ENABLED" if collect else "disabled"}')

        drag_count = 0
        try:
            for round_no in range(30):
                time.sleep(10)
                pausing = parameters.get('pause_during_drag', 'false') in (True, 'true')
                if pausing:
                    player.pause_mouse_load()
                try:
                    player.drag(player.component_by_name(my_card_name), 0, 100)
                    time.sleep(0.1)
                    player.drag(player.component_by_name(my_card_name), 0, -100)
                finally:
                    if pausing:
                        time.sleep(0.2)  # let the drag's own events drain before resuming
                        player.resume_mouse_load(hz=hz)
                drag_count += 1
                y = player.browser.execute_script(
                    "const el = document.querySelector(`.component[data-component-name='` + arguments[0] + `']`);"
                    "return el ? Math.round(el.getBoundingClientRect().y) : null;",
                    my_card_name)
                log(f'P{idx}: drag {drag_count} ok (card y={y})')
                if drag_count == 1:
                    dump_state(player, f'P{idx}_01_after_first_drag')
                if collect and drag_count % 6 == 0:
                    # What sustained_load does once per report interval: haul the whole
                    # accumulated send/receive log (thousands of objects at 30Hz) out of
                    # the page through WebDriver. Suspected of blocking the browser long
                    # enough that the next element lookup times out.
                    started = time.monotonic()
                    sent = player.collect_and_clear_mouse_send_log()
                    received = player.collect_and_clear_mouse_receive_log()
                    n_recv = sum(len(v) for v in received.values())
                    log(f'P{idx}: collected sent={len(sent)} received={n_recv} '
                        f'in {time.monotonic() - started:.1f}s')
            outcome = 'completed all rounds'
        except Exception as ex:
            log(f'P{idx}: drag failed after {drag_count} successful drags: {ex!r}')
            dump_state(player, f'P{idx}_99_at_failure')
            outcome = f'{type(ex).__name__} after {drag_count} drags: {traceback.format_exc()[-500:]}'

        result_queue.put({'worker': f'P{idx}', 'drags_ok': drag_count, 'outcome': outcome})
    finally:
        window.close()
