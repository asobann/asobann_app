from time import sleep
import pytest
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from .helper import GameHelper


@pytest.mark.usefixtures("server")
class TestCraftBox:
    def test_open(self, host: GameHelper):
        host.menu.open_craft_box.execute()
        host.should_see_component('CraftBox')

    def test_close(self, host: GameHelper):
        host.menu.open_craft_box.execute()
        host.menu.close_craft_box.execute()
        host.should_not_see_component('CraftBox')

    def test_use_export_table(self, host: GameHelper):
        host.menu.open_craft_box.execute()
        host.craft_box.use(host.craft_box.export_table)
        sleep(0.1)
        assert 'export?tablename' in host.current_url

    def test_crafting_kit_with_new_kit(self, host: GameHelper):
        host.menu.open_craft_box.execute()
        host.craft_box.use(host.craft_box.open_kit_box)
        host.craft_box.use(host.craft_box.kit_box.create_new)
        new_kit_json = host.craft_box.kit_box.raw_kit_json
        assert new_kit_json == {
            "kit": {},
            "components": [],
        }

    def test_dragging_textarea_does_not_move_component(self, host: GameHelper):
        host.menu.open_craft_box.execute()
        host.craft_box.use(host.craft_box.open_kit_box)

        left_before = host.component_by_name('KitBox').rect().left
        host.drag(host.component_by_name('KitBox'), 50, 50, grab_at='center')
        left_after = host.component_by_name('KitBox').rect().left
        assert left_before == left_after

    def test_dragging_textarea_does_not_scroll(self, host: GameHelper):
        host.menu.open_craft_box.execute()
        host.craft_box.use(host.craft_box.open_kit_box)

        left_before = host.component_by_name('KitBox').element.location['x']
        host.drag(host.component_by_name('KitBox'), 50, 50, grab_at='center')
        left_after = host.component_by_name('KitBox').element.location['x']
        assert left_before == left_after


@pytest.mark.usefixtures("server")
class TestCraftBoxWithOtherPlayers:
    def test_open_is_sync(self, host: GameHelper, another_player: GameHelper):
        another_player.go(host.current_url)
        another_player.menu.join("Player 2")

        host.menu.open_craft_box.execute()
        host.should_see_component('CraftBox')
        another_player.should_see_component('CraftBox')

    def test_close_by_another(self, host: GameHelper, another_player: GameHelper):
        another_player.go(host.current_url)
        another_player.menu.join("Player 2")

        host.menu.open_craft_box.execute()
        another_player.menu.close_craft_box.execute()
        host.should_not_see_component('CraftBox')
        another_player.should_not_see_component('CraftBox')

    def test_editing_json_is_sync(self, host: GameHelper, another_player: GameHelper):
        another_player.go(host.current_url)
        another_player.menu.join("Player 2")

        host.menu.open_craft_box.execute()
        host.craft_box.use(host.craft_box.open_kit_box)
        host.craft_box.use(host.craft_box.kit_box.create_new)
        host.craft_box.kit_box.send_keys_to_editor([Keys.ARROW_UP, '"dummy": "This is test",', Keys.RETURN])
        assert host.craft_box.kit_box.raw_kit_json == {
            "dummy": "This is test",
            "kit": {},
            "components": [],
        }

        host.click(host.component(1))  # lose focus from textarea
        sleep(0.1)  # should_have_text() does not work with textarea somehow
        assert another_player.craft_box.kit_box.raw_kit_json == {
            "dummy": "This is test",
            "kit": {},
            "components": [],
        }

