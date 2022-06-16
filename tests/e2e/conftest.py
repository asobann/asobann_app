import os
import subprocess
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

import pytest

from .helper import GameHelper

firefox_options = Options()


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
    browser = webdriver.Firefox(options=firefox_options)
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
    browser = webdriver.Firefox()
    yield browser
    if 'ASOBANN_KEEP_TEST_BROWSER' not in os.environ:
        browser.close()


@pytest.fixture
def another_browser(another_browser_window):
    another_browser_window.delete_all_cookies()
    yield another_browser_window


@pytest.fixture
def another_player(another_browser):
    return GameHelper.player(another_browser)


@pytest.fixture
def browser_factory():
    browsers = []
    def factory():
        browser = webdriver.Firefox()
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


class Uploader:
    def __init__(self, test_file_dir):
        self.test_file_dir = test_file_dir

    def upload_kit_from_file_with_craft_box(self, player: GameHelper, filename, image_filenames=[]):
        player.menu.open_craft_box.execute()
        player.craft_box.use(player.craft_box.upload_kit)
        player.craft_box.upload_kit.select_json_file(str(self.test_file_dir / filename))
        if image_filenames:
            image_paths = [str(self.test_file_dir / fn) for fn in image_filenames]
            player.craft_box.upload_kit.select_image_files('\n'.join(image_paths))
        player.craft_box.upload_kit.upload()
        player.craft_box.upload_kit.accept_success_alert()


@pytest.fixture
def uploader(request):
    return Uploader(Path(request.module.__file__).parent)


