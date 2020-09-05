import subprocess

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

import pytest

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
    # browser.close()


@pytest.fixture
def browser(browser_window):
    browser_window.delete_all_cookies()
    return browser_window


def browser_func(headless=False):
    firefox_options.headless = headless
    browser = webdriver.Firefox(options=firefox_options)
    browser.delete_all_cookies()
    return browser


@pytest.fixture(scope='session')
def another_browser_window(firefox_driver):
    browser = webdriver.Firefox()
    yield browser
    # browser.close()


@pytest.fixture
def another_browser(another_browser_window):
    another_browser_window.delete_all_cookies()
    yield another_browser_window


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
