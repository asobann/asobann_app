from pathlib import Path
import pytest
from selenium import webdriver
from ..helper import GameHelper


@pytest.mark.usefixtures("server")
@pytest.mark.usefixtures("default_kits_and_components")
class TestUploadKit:
    def test_success(self, browser: webdriver.Firefox, uploader: 'Uploader'):
        host = GameHelper.player(browser)
        uploader.upload_kit_from_file_with_craft_box(host, 'test_menu_kit.json')

        host.menu.add_kit.execute()
        host.menu.should_see_kit("Test Kit")

    def test_cancel(self, browser: webdriver.Firefox):
        host = GameHelper.player(browser)

        host.menu.open_craft_box.execute()
        host.craft_box.use(host.craft_box.upload_kit)
        host.craft_box.upload_kit.cancel()

        host.menu.add_kit.execute()
        host.menu.should_not_see_kit("Test Kit")

    def test_no_jsonfile(self, browser: webdriver.Firefox):
        host = GameHelper.player(browser)

        host.menu.open_craft_box.execute()
        host.craft_box.use(host.craft_box.upload_kit)
        host.craft_box.upload_kit.upload()
        host.craft_box.upload_kit.accept_failure_alert()

        host.menu.add_kit.execute()
        host.menu.should_not_see_kit("Test Kit")

    class TestUploadImage:
        def test_one_image(self, browser: webdriver.Firefox, uploader: 'Uploader'):
            host = GameHelper.player(browser)
            uploader.upload_kit_from_file_with_craft_box(host, 'test_menu_kit_with_one_image.json', ['example.png'])

            host.menu.add_kit.execute()
            host.menu.add_kit_from_list("Test Kit")
            host.menu.add_kit_done()

            assert '/images/uploaded/example.png' in host.component_by_name('Test Component').face()

        @pytest.mark.skip
        def test_image(self, browser: webdriver.Firefox):
            pass

        @pytest.mark.skip
        def test_faceup_image(self, browser: webdriver.Firefox):
            pass

        @pytest.mark.skip
        def test_facedown_image(self, browser: webdriver.Firefox):
            pass

        @pytest.mark.skip
        def test_multiple_images(self, browser: webdriver.Firefox):
            pass


@pytest.mark.usefixtures("server")
class TestCounterKit:
    def test_upload_and_use(self, browser: webdriver.Firefox, uploader: 'Uploader'):
        host = GameHelper.player(browser)
        uploader.upload_kit_from_file_with_craft_box(host, 'test_counter_kit.json')

        host.menu.add_kit.execute()
        host.menu.should_see_kit("Counter Kit")
        host.menu.add_kit_from_list("Counter Kit")
        host.menu.add_kit_done()

        host.should_have_text("Counter Name")
