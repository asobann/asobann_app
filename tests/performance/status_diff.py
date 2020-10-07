from selenium.common.exceptions import NoSuchElementException, TimeoutException
from ..e2e.helper import compo_pos, Rect, GameHelper, STAGING_TOP


saved_status = []


def gather_status(player: GameHelper):
    status = []
    n = 1
    while True:
        try:
            c = player.component(n, wait=False)
            status.append((str(c.rect()), c.face()))
            n += 1
        except NoSuchElementException:
            break
    return status


def save_status(iteration, tag, status: list):
    while iteration > len(saved_status) - 1:
        saved_status.append({})
    saved_status[iteration][tag] = status



def evaluate_saved_status(baseline_key=0):
    diff = {'count': 0, 'diffs': []}
    for iter, statuses_in_iteration in enumerate(saved_status):
        baseline = statuses_in_iteration[baseline_key]
        for status in [statuses_in_iteration[key] for key in statuses_in_iteration.keys() if key != baseline_key]:
            for i, c in enumerate(status):
                if baseline[i] != c:
                    diff['diffs'].append(f"diff on iteration {iter + 1} at index {i} <{baseline[i]}> <{c}>")
                    diff['count'] += 1
                    break  # don't count diffs for same component
    return diff


