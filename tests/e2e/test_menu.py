from time import sleep
from pathlib import Path
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from .helper import GameHelper, TOP


@pytest.mark.usefixtures("server")
class TestToolbox:
    def test_open(self, browser: webdriver.Firefox):
        host = GameHelper.player(browser)

        host.menu.open_toolbox.execute()
        host.should_see_component('Toolbox')

    def test_close(self, browser: webdriver.Firefox):
        host = GameHelper.player(browser)

        host.menu.open_toolbox.execute()
        host.menu.close_toolbox.execute()
        host.should_not_see_component('Toolbox')

    def test_use_export_table(self, browser: webdriver.Firefox):
        host = GameHelper.player(browser)

        host.menu.open_toolbox.execute()
        host.toolbox.use(host.toolbox.export_table)
        sleep(0.1)
        assert 'export?tablename' in host.current_url

