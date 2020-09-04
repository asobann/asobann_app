from time import sleep
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

    def test_use_export_table(self, browser: webdriver.Firefox):
        host = GameHelper.player(browser)

        host.menu.open_toolbox.execute()
        host.click_at(host.component_by_name('Export Table'), By.CSS_SELECTOR, 'button')
        sleep(0.1)
        assert 'export?tablename' in host.current_url
