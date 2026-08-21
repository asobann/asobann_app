import json
import os
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

import pytest
import pytest_asyncio

from .helper import GameHelper, Uploader

# These tests drive several real browsers against a live server and assert on state that
# arrives asynchronously, so they are inherently flaky - a retry is the practical answer.
# Applied here rather than in pyproject.toml's addopts on purpose: the unit tests must
# NOT be retried, because there a second attempt would only hide a real defect.
E2E_RERUNS = 3
E2E_RERUNS_DELAY = 2

# Tests known to fail intermittently. Flakiness here is a *probabilistic property*, not a
# defect waiting to be fixed: a test that passes sometimes and fails sometimes is, as a
# verdict, a passing test. These get extra attempts so that verdict is reached reliably.
#
# The point of the list is the *contrast*: a failure in a test that is NOT listed here is
# a strong signal that something actually broke. That distinction is what makes this suite
# usable as a safety net for the asyncio migration.
#
# Not xfail: xfail would also swallow a *consistent* failure. Failing every attempt is
# exactly how "this is not flaky, it is broken" shows up, and that signal must survive.
# See E2E_TOLERATE_KNOWN_FLAKY below for how CI is kept green without losing it.
#
# 出入りのルール（コストの高い調査に引きずり込まれないための取り決め）:
#   - 新規テスト、または既存テストに影響しうる変更は、まず**単独実行でグリーン**にする
#     （開発の一部。全件実行の中で初めて確認するものではない）
#   - 全件実行して落ちたテストがこの一覧に無ければ、**単独実行で再確認する**
#     - 単独実行でグリーンになったら、フレーキー候補としてこの一覧に載せる
#     - 単独実行でも落ちたら、それは実際の失敗。原因を調べて直す
#   - 一覧に載せた後も、**1回成功しただけでは一覧から外さない**。しばらく連続して
#     成功することを見てから外す
#   - CI（まだ無い。そのうち作る）では、一覧にあるテストが落ちてもビルドは赤くしない。
#     ただし**CI環境で連続して落ち続ける**テストは、フレーキーではなく壊れている疑いが
#     あるものとして監視し、イシュー化する（自動化はまだで、今は人かAIが気づいたら対応する）
#   - 動機は、フレーキーの調査・対応はコストが高くROIが低いこと。いちいち気にせず、
#     気にすべきときにシグナルが上がる状態を保つのが肝心
E2E_KNOWN_FLAKY_RERUNS = 5
E2E_KNOWN_FLAKY = {
    # 2026-08-10: 全件実行を複数回まわしたところ、落ちる顔ぶれが毎回入れ替わった。
    'test_component.py::test_moving_box_does_not_lose_things_within',
    'test_session.py::TestOutOfSync::test_move_box_of_card_bit_by_bit',
    'test_craft_box.py::TestCraftBoxWithOtherPlayers::test_editing_json_is_sync',

    # 2026-08-11: helper.should_be_joined() を入れて頻度は明確に下がった（観戦者ガードで
    # 操作が無言に捨てられていた分は消えた。#127）が、全89件ではまだ再発する。
    # 一度は一覧から外したものの、根拠が部分実行1回だけだったので戻した。上の出入りの
    # ルールのとおり、連続で成功することを確認してから外すこと。
    # なお test_flipped_and_image_change は setup 側で落ちることもある（キット追加の
    # timeout）。他のTestGluedでは同じsetupが通っているので、これもフレーキーとして扱う。
    'test_component.py::TestGlued::test_flipped_and_text_hides',
    'test_component.py::TestGlued::test_flipped_and_image_change',
    'test_component.py::TestGlued::test_put_in_hand_area_and_text_hides',

    # 2026-08-11に追加: 元から落ちていたが未登録だった。textarea が出ないことがある。
    'test_component.py::TestEditable::test_editing',
    'test_component.py::TestEditable::test_editing_is_shared',

    # 2026-08-11: asyncio移行(Quart化)後の全件実行2回で一覧外の失敗として出た。
    # いずれも単独実行では毎回グリーン(出入りのルールどおり確認済み)なので、フル
    # スイート実行特有のタイミング競合と判断してここに追加する。2回とも顔ぶれが
    # 完全に入れ替わっており、特定の一貫した壊れ方ではない。
    'test_component.py::TestHandArea::test_cards_on_hand_area_follows_when_hand_area_is_moved',
    'test_component.py::TestHandArea::test_cards_in_hand_are_looks_facedown',
    'test_component.py::TestHandArea::test_resizing_hand_area_updates_ownership',
    'test_component.py::TestHandArea::test_up_card_in_my_hand_become_down_when_moved_to_others_hand',
    'test_component.py::TestHandArea::test_many_cards_on_hand_area_move_with_the_area',
    'test_playing_card_kit.py::test_load_playing_card_kit',
    'test_cardistry.py::TestSpreadOutAndCollect::test_can_collect_cards_in_hand_area',

    # 2026-08-11: フロントエンド依存の全面最新化(webpack/jest/redom等)後の全件実行で
    # 一覧外の失敗として出た。単独実行では毎回グリーン(確認済み)。
    'test_cardistry.py::TestSpreadOutAndCollect::test_can_ignore_cards_in_hand_area',
    'test_cardistry.py::TestFlipAll::test_to_face_down_if_any_are_face_up',
}

# CI では、既知フレーキーが全リトライ落ちしてもビルドを赤くしたくない。ただし結果は
# 握り潰さず必ず出力する。一覧に無いテストが1件でも落ちれば、これまでどおり赤くなる。
E2E_TOLERATE_KNOWN_FLAKY = os.environ.get('E2E_TOLERATE_KNOWN_FLAKY') == '1'


def _is_known_flaky_nodeid(nodeid: str) -> bool:
    # nodeid looks like 'tests/e2e/test_component.py::TestHandArea::test_x'
    #
    # endswith ではなく完全一致で見る。endswith には2つの穴があった:
    #   - パラメータ化すると nodeid が '...::test_x[case1]' になり、一覧に載って
    #     いてもマッチせずリトライ回数が5から3に落ちる
    #   - 別ファイルの同名クラス・同名テストにも当たりうる
    # どちらも今の顔ぶれでは表面化していないが、一覧に足すたびに踏みうる。
    #
    # パラメータ化テストを一覧に載せたくなったら、'[' の前で切って比べる形に
    # 変えること（今は該当が無いので単純な等価比較にしてある）。
    return nodeid in {f'tests/e2e/{entry}' for entry in E2E_KNOWN_FLAKY}


def _is_known_flaky(item) -> bool:
    return _is_known_flaky_nodeid(item.nodeid)


def _split_failures(terminalreporter):
    """
    Return (known_flaky_nodeids, other_nodeids) for the run's *final* verdicts.

    Read from terminalreporter.stats rather than collecting in a pytest_runtest_makereport
    hook: pytest-rerunfailures files each retried attempt under stats['rerun'] and only the
    last one under stats['failed'], whereas the makereport hook sees every attempt as a
    plain failure (which listed the same test six times).
    """
    known, other = [], []
    for report in terminalreporter.stats.get('failed', []):
        (known if _is_known_flaky_nodeid(report.nodeid) else other).append(report.nodeid)
    return known, other


def pytest_terminal_summary(terminalreporter):
    known, other = _split_failures(terminalreporter)
    if not known:
        return
    terminalreporter.section('known-flaky tests that failed every attempt')
    for nodeid in known:
        terminalreporter.write_line(f'  {nodeid}')
    terminalreporter.write_line(
        'これらは tests/e2e/conftest.py の E2E_KNOWN_FLAKY に載っている。'
        '毎回すべて落ちるならフレーキーではなく壊れているので、一覧から外して調べること。')
    if E2E_TOLERATE_KNOWN_FLAKY:
        if other:
            terminalreporter.write_line(
                f'E2E_TOLERATE_KNOWN_FLAKY は有効だが、一覧に無い失敗が {len(other)} 件あるので'
                f'この実行は失敗として扱う。')
        else:
            terminalreporter.write_line(
                'E2E_TOLERATE_KNOWN_FLAKY が有効で、失敗はすべて既知フレーキーだったため'
                '終了コードは0にする。')


def pytest_sessionfinish(session, exitstatus):
    _write_history(session, exitstatus)

    if not E2E_TOLERATE_KNOWN_FLAKY:
        return
    terminalreporter = session.config.pluginmanager.getplugin('terminalreporter')
    if terminalreporter is None:
        return
    known, other = _split_failures(terminalreporter)
    # Only forgive when *every* failure was a known-flaky one. A single unlisted failure
    # must still fail the run.
    if known and not other:
        session.exitstatus = 0


def pytest_collection_modifyitems(items):
    # このフックはこのconftest.py(tests/e2e/)が登録されるだけで、テストセッション全体の
    # itemsを受け取る。パスで絞らないと、`uv run pytest`(引数無し。CLAUDE.mdが案内する
    # 実行方法そのもの)でtests/e2eと一緒にunit/functional/apiも集められたとき、
    # それらにまでflakyマーカーが付いてしまう。ユニットテストに意図的に適用していない
    # (再試行すると本物の不具合を隠すため)という方針の実害ある違反になる。
    for item in items:
        if 'tests/e2e/' not in str(item.path).replace('\\', '/'):
            continue
        if item.get_closest_marker('flaky') is not None:
            continue
        reruns = E2E_KNOWN_FLAKY_RERUNS if _is_known_flaky(item) else E2E_RERUNS
        item.add_marker(pytest.mark.flaky(reruns=reruns, reruns_delay=E2E_RERUNS_DELAY))


# ---- 実行履歴の記録 ----
#
# 1回のスイート実行を、試行(attempt)単位でJSONに書き出す。「常連フレーキーの中に
# 直せるものがあるか」「フレーキーだと思っているが実は壊れているテストがあるか」を
# 判定するための材料。SQLiteへの取り込みや分析は別の作業で、ここではまず
# 漏らさず残すことだけをやる。
#
# report.rerun (0始まりの試行番号) と report.outcome=='rerun' は pytest-rerunfailures
# 自身が全レポートに付ける(ソースで確認済み: item.execution_count-1がreport.rerunに
# なる)。対象は必ず tests/e2e/ 配下で、flakyマーカーは全件に付いている
# (pytest_collection_modifyitemsを見よ)ので、この属性は毎回付いている前提でよい。
_HISTORY_RUN = {}
_HISTORY_ATTEMPTS = {}   # nodeid -> [attempt dict, ...]
_HISTORY_ORDER = []      # 実行順に並んだnodeid(初出のときだけ追加)


def _history_dir():
    path = os.environ.get('ASOBANN_E2E_HISTORY')
    return Path(path) if path else None


def _capture_browser_info(browser):
    if 'browser' in _HISTORY_RUN:
        return
    try:
        caps = browser.capabilities
        _HISTORY_RUN['browser'] = caps.get('browserName')
        _HISTORY_RUN['browser_version'] = caps.get('browserVersion')
    except Exception:
        pass


def pytest_sessionstart(session):
    if _history_dir() is None:
        return
    config = session.config
    _HISTORY_RUN.update({
        'run_id': str(uuid.uuid4()),
        'started_at': datetime.now(timezone.utc).astimezone().isoformat(),
        'origin': os.environ.get('ASOBANN_E2E_RUN_ORIGIN', 'local'),
        'machine': os.environ.get('ASOBANN_E2E_MACHINE'),
        'cpu_count': os.cpu_count(),
        'git_sha': os.environ.get('ASOBANN_GIT_SHA'),
        'git_dirty': os.environ.get('ASOBANN_GIT_DIRTY') == '1',
        'e2e_image': os.environ.get('ASOBANN_E2E_IMAGE_TAG'),
        'dev_mode': os.environ.get('ASOBANN_E2E_DEV_MODE') == 'yes',
        'randomly_seed': config.getoption('randomly_seed', None),
        'pytest_args': list(config.invocation_params.args),
        'reruns': E2E_RERUNS,
        'known_flaky_reruns': E2E_KNOWN_FLAKY_RERUNS,
        'reruns_delay': E2E_RERUNS_DELAY,
        'tolerate_known_flaky': E2E_TOLERATE_KNOWN_FLAKY,
        'known_flaky_list': sorted(E2E_KNOWN_FLAKY),
        'headless': os.environ.get('MOZ_HEADLESS') == '1',
        'slowmo': float(os.environ.get('ASOBANN_E2E_SLOWMO', '0')),
    })


def _failure_summary(report):
    if not report.longrepr:
        return None
    try:
        return report.longrepr.reprcrash.message
    except AttributeError:
        pass
    text = report.longreprtext.strip()
    return text.splitlines()[0] if text else None


def pytest_runtest_logreport(report):
    if _history_dir() is None:
        return
    if 'tests/e2e/' not in report.nodeid.replace('\\', '/'):
        return
    attempt_number = getattr(report, 'rerun', 0)
    nodeid = report.nodeid
    attempts = _HISTORY_ATTEMPTS.setdefault(nodeid, [])
    if nodeid not in _HISTORY_ORDER:
        _HISTORY_ORDER.append(nodeid)

    current = next((a for a in attempts if a['attempt'] == attempt_number), None)
    if current is None:
        current = {
            'attempt': attempt_number,
            'phase_failed': None,
            'outcome': 'passed',
            'duration_s': 0.0,
            'started_at': datetime.fromtimestamp(report.start, tz=timezone.utc).astimezone().isoformat(),
            'failure_summary': None,
        }
        attempts.append(current)

    current['duration_s'] += report.duration
    if report.outcome != 'passed':
        current['outcome'] = report.outcome
        if report.when != 'teardown':
            current['phase_failed'] = report.when
        if report.failed or report.outcome == 'rerun':
            current['failure_summary'] = _failure_summary(report)


def _final_outcome(attempts):
    last = attempts[-1]
    if last['outcome'] == 'skipped':
        return 'skipped'
    if last['outcome'] in ('failed', 'error'):
        return last['outcome'] + '_all_retries' if len(attempts) > 1 else last['outcome']
    return 'passed_after_retry' if len(attempts) > 1 else 'passed'


def _write_history(session, exitstatus):
    out = _history_dir()
    if out is None or not _HISTORY_RUN:
        return
    _HISTORY_RUN['finished_at'] = datetime.now(timezone.utc).astimezone().isoformat()
    _HISTORY_RUN['exit_status'] = int(exitstatus)
    results = []
    for order_index, nodeid in enumerate(_HISTORY_ORDER):
        attempts = sorted(_HISTORY_ATTEMPTS[nodeid], key=lambda a: a['attempt'])
        results.append({
            'nodeid': nodeid,
            'order_index': order_index,
            'final_outcome': _final_outcome(attempts),
            'attempts': attempts,
        })
    payload = {'schema_version': 1, 'run': _HISTORY_RUN, 'results': results}
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{_HISTORY_RUN['run_id']}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


firefox_options = Options()

# The e2e tests drag components to absolute coordinates up to roughly y=750 and were
# written against a normal desktop-sized window. Headless Firefox defaults to a viewport
# of 1366x634, so those drags fail with MoveTargetOutOfBoundsException and every
# assertion that follows times out. Size the window explicitly rather than depending on
# whatever the driver picks. Applied per browser (see new_e2e_browser) instead of via
# the shared `firefox_options`, to keep the change scoped to E2E browsers.
E2E_WINDOW_SIZE = (1600, 1200)


# 失敗時にスクリーンショットを撮るため、開いているブラウザを覚えておく。
#
# このスイートの失敗は「2つのブラウザで見えているものが違う」種類なので、
# **全部を撮らないと診断にならない**。片方だけでは判断できない。
_live_browsers = []


def new_e2e_browser(options=None):
    browser = webdriver.Firefox(options=options) if options else webdriver.Firefox()
    browser.set_window_size(*E2E_WINDOW_SIZE)
    _live_browsers.append(browser)
    _untrack_when_closed(browser)
    _capture_browser_info(browser)
    return browser


def _untrack_when_closed(browser):
    """close/quit された時点で、覚えておく対象から外す。

    `browser_factory` はテストごとにブラウザを作って teardown で閉じるので、
    放っておくと閉じたドライバがセッション中ずっと溜まる。撮影のたびに死んだ
    ドライバへ save_screenshot を投げて例外を握りつぶすことになり、実行数に
    比例して無駄が増える。

    閉じる側で明示的に外す（close を呼ぶ箇所で1行足す）やり方もあるが、それだと
    今後ブラウザを閉じるコードが増えたときに漏れる。ドライバ自身に紐づけておく。
    """
    def unhook(name):
        original = getattr(browser, name)

        def wrapped(*args, **kwargs):
            try:
                return original(*args, **kwargs)
            finally:
                if browser in _live_browsers:
                    _live_browsers.remove(browser)

        setattr(browser, name, wrapped)

    for name in ('close', 'quit'):
        unhook(name)


def _artifacts_dir():
    path = os.environ.get('ASOBANN_E2E_ARTIFACTS')
    return Path(path) if path else None


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """失敗したテストのスクリーンショットを、開いている全ブラウザぶん残す。

    リトライごとに撮る（ファイル名に試行番号を入れる）。「1回目は失敗、2回目は成功」
    の差分が、フレーキーの調査でいちばん見たいもの。

    撮影で例外が出てもテストの結果は変えない。ブラウザが死んでいる、セッションが
    切れている、といった状況こそ撮りたい場面だが、そこで落ちて本来の失敗理由を
    隠してしまっては本末転倒。
    """
    outcome = yield
    report = outcome.get_result()
    if not report.failed:
        return
    out = _artifacts_dir()
    if out is None or not _live_browsers:
        return

    safe = re.sub(r'[^A-Za-z0-9_.-]', '_', item.nodeid)
    attempt = getattr(item, 'execution_count', None)
    suffix = f'_try{attempt}' if attempt else ''
    out.mkdir(parents=True, exist_ok=True)
    for i, browser in enumerate(_live_browsers, start=1):
        try:
            browser.save_screenshot(str(out / f'{safe}{suffix}_browser{i}.png'))
        except Exception:
            pass


@pytest.fixture(scope='session')
def firefox_driver():
    proc = subprocess.run("which geckodriver", stdout=subprocess.DEVNULL, shell=True)
    if proc.returncode == 0:
        return

    # download firefox driver (geckodriver) for 64bit on ~/bin
    subprocess.run(
        "cd ~/bin && "
        "curl -L https://github.com/mozilla/geckodriver/releases/download/v0.26.0/geckodriver-v0.26.0-linux64.tar.gz"
        " | tar zxv", shell=True)


@pytest.fixture(scope='session')
def headless():
    # selenium 4.10 で Options.headless セッターが削除された。-headless引数で代替する。
    firefox_options.add_argument('-headless')


@pytest.fixture(scope='session')
def browser_window(firefox_driver):
    browser = new_e2e_browser(firefox_options)
    yield browser
    if 'ASOBANN_KEEP_TEST_BROWSER' not in os.environ:
        browser.close()


@pytest.fixture
def browser(browser_window):
    browser_window.delete_all_cookies()
    return browser_window


@pytest.fixture
def host(browser):
    return GameHelper.player(browser)


def browser_func(headless=False):
    # 呼び出しごとに独立したOptionsにする。共有の firefox_options に足すと
    # 繰り返し呼ばれたとき -headless 引数が重複して溜まっていく。
    options = Options()
    if headless:
        options.add_argument('-headless')
    browser = webdriver.Firefox(options=options)
    browser.delete_all_cookies()
    return browser


@pytest.fixture(scope='session')
def another_browser_window(firefox_driver):
    browser = new_e2e_browser()
    yield browser
    if 'ASOBANN_KEEP_TEST_BROWSER' not in os.environ:
        browser.close()


@pytest.fixture
def another_browser(another_browser_window):
    another_browser_window.delete_all_cookies()
    yield another_browser_window


@pytest.fixture
def another_player(another_browser, host):
    another_player = GameHelper.player(another_browser)
    another_player.go(host.current_url)
    another_player.menu.join("Player 2")
    return another_player


@pytest.fixture
def browser_factory():
    browsers = []
    def factory():
        browser = new_e2e_browser()
        browsers.append(browser)
        return browser
    yield factory

    for b in browsers:
        b.close()


@pytest_asyncio.fixture(scope='session')
async def in_mem_app():
    import asobann.app
    return await asobann.app.create_app(testing=True)


@pytest_asyncio.fixture(autouse=True)
async def tables(in_mem_app):
    # clear all documents in tables collection
    from asobann.store import tables
    await tables.purge_all()


@pytest.fixture(scope='function')
def default_kits_and_components(deploy_data):
    pass


@pytest.fixture
def uploader(request, base_url):
    return Uploader(test_file_dir=Path(request.module.__file__).parent, base_url=base_url)


