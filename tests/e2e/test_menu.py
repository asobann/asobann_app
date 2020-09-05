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

    def test_use_export_table(self, browser: webdriver.Firefox):
        host = GameHelper.player(browser)

        host.menu.open_toolbox.execute()
        host.toolbox.use(host.toolbox.export_table)
        sleep(0.1)
        assert 'export?tablename' in host.current_url

    class TestUploadKit:
        def test_success(self, browser: webdriver.Firefox):
            host = GameHelper.player(browser)

            host.menu.open_toolbox.execute()
            host.toolbox.use(host.toolbox.upload_kit)
            host.toolbox.upload_kit.select_json_file(str(Path(__file__).parent / 'test_menu_kit.json'))
            host.toolbox.upload_kit.upload()
            host.toolbox.upload_kit.accept_success_alert()

            host.menu.add_kit.execute()
            host.menu.should_see_kit("Test Kit")

        def test_no_jsonfile(self, browser: webdriver.Firefox):
            host = GameHelper.player(browser)

            host.menu.open_toolbox.execute()
            host.toolbox.use(host.toolbox.upload_kit)
            host.toolbox.upload_kit.upload()
            host.toolbox.upload_kit.accept_failure_alert()

            host.menu.add_kit.execute()
            host.menu.should_see_kit("Test Kit")
