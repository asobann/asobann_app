import pytest
from selenium import webdriver
from .helper import GameHelper, TOP


@pytest.mark.usefixtures("server")
class TestToolbox:
    def test_open(self, browser: webdriver.Firefox):
        host = GameHelper.player(browser)

        host.menu.open_toolbox.execute()
        host.should_see_component('toolbox')
