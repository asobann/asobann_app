from time import sleep
from pathlib import Path
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from .helper import GameHelper, TOP
from .craft_box_helper import CraftBox


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

    def test_crafting_kit_with_new_kit(self, browser: webdriver.Firefox):
        host: GameHelper = GameHelper.player(browser)

        host.menu.open_craft_box.execute()
        host.craft_box.use(host.craft_box.open_kit_box)
        host.craft_box.use(host.craft_box.kit_box.create_new)
        new_kit_json = host.craft_box.kit_box.raw_kit_json
        assert new_kit_json == {
            "kit": {},
            "components": [],
        }

    def test_dragging_textarea_does_not_move_component(self, browser: webdriver.Firefox):
        host: GameHelper = GameHelper.player(browser)

        host.menu.open_craft_box.execute()
        host.craft_box.use(host.craft_box.open_kit_box)

        left_before = host.component_by_name('KitBox').rect().left
        host.drag(host.component_by_name('KitBox'), 50, 50, grab_at='center')
        left_after = host.component_by_name('KitBox').rect().left
        assert left_before == left_after

    def test_dragging_textarea_does_not_scroll(self, browser: webdriver.Firefox):
        host: GameHelper = GameHelper.player(browser)

        host.menu.open_craft_box.execute()
        host.craft_box.use(host.craft_box.open_kit_box)

        left_before = host.component_by_name('KitBox').element.location['x']
        host.drag(host.component_by_name('KitBox'), 50, 50, grab_at='center')
        left_after = host.component_by_name('KitBox').element.location['x']
        assert left_before == left_after


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
