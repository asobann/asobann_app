import os
import subprocess
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

import pytest

from .helper import GameHelper, Uploader

# These tests drive several real browsers against a live server and assert on state that
# arrives asynchronously, so they are inherently flaky - a retry is the practical answer.
# Applied here rather than in pyproject.toml's addopts on purpose: the unit tests must
# NOT be retried, because there a second attempt would only hide a real defect.
E2E_RERUNS = 2
E2E_RERUNS_DELAY = 2


def pytest_collection_modifyitems(items):
    for item in items:
        if item.get_closest_marker('flaky') is None:
            item.add_marker(pytest.mark.flaky(reruns=E2E_RERUNS, reruns_delay=E2E_RERUNS_DELAY))


firefox_options = Options()

# The e2e tests drag components to absolute coordinates up to roughly y=750 and were
# written against a normal desktop-sized window. Headless Firefox defaults to a viewport
# of 1366x634, so those drags fail with MoveTargetOutOfBoundsException and every
# assertion that follows times out. Size the window explicitly rather than depending on
# whatever the driver picks. Applied per browser (see new_e2e_browser) instead of via
# the shared `firefox_options`, because that object is also used by the performance
# tests' browser_func and changing their window size would shift the load-test baseline.
E2E_WINDOW_SIZE = (1600, 1200)


def new_e2e_browser(options=None):
    browser = webdriver.Firefox(options=options) if options else webdriver.Firefox()
    browser.set_window_size(*E2E_WINDOW_SIZE)
    return browser


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
    firefox_options.headless = True


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
    firefox_options.headless = headless
    browser = webdriver.Firefox(options=firefox_options)
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


@pytest.fixture(scope='session')
def in_mem_app():
    import asobann.app
    return asobann.app.create_app(testing=True)


@pytest.fixture(autouse=True)
def tables(in_mem_app):
    # clear all documents in tables collection
    from asobann.store import tables
    tables.purge_all()


@pytest.fixture(scope='function')
def default_kits_and_components(deploy_data):
    pass


@pytest.fixture
def uploader(request, base_url):
    return Uploader(test_file_dir=Path(request.module.__file__).parent, base_url=base_url)


