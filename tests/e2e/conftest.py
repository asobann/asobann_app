import os
import subprocess
import time

from selenium import webdriver

import pytest


@pytest.fixture(scope='session')
def server():
    os.environ["FLASK_ENV"] = "test"
    with subprocess.Popen(["/usr/local/bin/pipenv", "run", "python", "-m", "asobann.test_server"], env=os.environ) as proc:
        time.sleep(1)
        yield
        proc.terminate()


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
def browser_window(firefox_driver):
    browser = webdriver.Firefox()
    yield browser
    # browser.close()


@pytest.fixture
def browser(browser_window):
    browser_window.delete_all_cookies()
    yield browser_window


@pytest.fixture(scope='session')
def another_browser_window(firefox_driver):
    browser = webdriver.Firefox()
    yield browser
    # browser.close()


@pytest.fixture
def another_browser(another_browser_window):
    another_browser_window.delete_all_cookies()
    yield another_browser_window


@pytest.fixture(scope='session')
def in_mem_app():
    from asobann import test_server
    return test_server.app


@pytest.fixture(autouse=True)
def tables(in_mem_app):
    # clear all documents in tables collection
    from asobann import tables
    tables.purge_all()



