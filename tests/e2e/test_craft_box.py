from time import sleep
from pathlib import Path
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from .helper import GameHelper, TOP


@pytest.mark.usefixtures("server")
class TestCraftBox:
    def test_open(self, browser: webdriver.Firefox):
        host = GameHelper.player(browser)

        host.menu.open_craft_box.execute()
        host.should_see_component('CraftBox')

    def test_close(self, browser: webdriver.Firefox):
        host = GameHelper.player(browser)

        host.menu.open_craft_box.execute()
        host.menu.close_craft_box.execute()
        host.should_not_see_component('CraftBox')

    def test_use_export_table(self, browser: webdriver.Firefox):
        host: GameHelper = GameHelper.player(browser)

        host.menu.open_craft_box.execute()
        host.craft_box.use(host.craft_box.export_table)
        sleep(0.1)
        assert 'export?tablename' in host.current_url


@pytest.mark.usefixtures("server")
class TestCraftBoxWithOtherPlayers:
    def test_open_is_sync(self, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
        host = GameHelper.player(browser)

        another = GameHelper.player(another_browser)
        another.go(host.current_url)
        another.menu.join("Player 2")

        host.menu.open_craft_box.execute()
        host.should_see_component('CraftBox')
        another.should_see_component('CraftBox')

    def test_close_by_another(self, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
        host = GameHelper.player(browser)

        another = GameHelper.player(another_browser)
        another.go(host.current_url)
        another.menu.join("Player 2")

        host.menu.open_craft_box.execute()
        another.menu.close_craft_box.execute()
        host.should_not_see_component('CraftBox')
        another.should_not_see_component('CraftBox')
