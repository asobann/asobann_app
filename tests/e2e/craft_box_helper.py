import json
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.common.by import By


class CraftBox:
    class UploadKit:
        def __init__(self, craft_box: 'CraftBox'):
            self.craft_box = craft_box

        def select_json_file(self, filepath):
            file_input = self.craft_box.browser.find_element(by=By.CSS_SELECTOR, value='form input#data')
            file_input.send_keys(filepath)

        def select_image_files(self, filepath):
            file_input = self.craft_box.browser.find_element(by=By.CSS_SELECTOR, value='form input#images')
            file_input.send_keys(filepath)

        def upload(self):
            self.craft_box.browser.find_element(by=By.CSS_SELECTOR, value='form button#upload').click()

        def cancel(self):
            self.craft_box.browser.find_element(by=By.CSS_SELECTOR, value='form button#cancel').click()

        def accept_success_alert(self):
            self.craft_box.helper.accept_alert('Upload Success!')

        def accept_failure_alert(self):
            self.craft_box.helper.accept_alert('^Upload Failed:.*', regex_match=True)

    class KitBox:
        def __init__(self, craft_box: 'CraftBox'):
            self.craft_box = craft_box
            self.create_new = object()

        @property
        def raw_kit_json(self):
            browser: WebDriver = self.craft_box.helper.browser
            el: WebElement = self.craft_box.helper.browser.find_element(by=By.CSS_SELECTOR, value="textarea#kit_json")
            return json.loads(el.get_attribute('value'))

    def __init__(self, browser: WebDriver, helper: 'GameHelper'):
        self.browser = browser
        self.helper = helper
        self.upload_kit: 'CraftBox.UploadKit' = CraftBox.UploadKit(self)
        self.export_table = object()
        self.open_kit_box = object()
        self.kit_box: 'CraftBox.KitBox' = CraftBox.KitBox(self)

    def use(self, tool):
        match tool:
            case self.upload_kit:
                self.helper.click_at(self.helper.component_by_name('CraftBox'), By.CSS_SELECTOR, 'button#upload_kit')
            case self.export_table:
                self.helper.click_at(self.helper.component_by_name('CraftBox'), By.CSS_SELECTOR, 'button#export_table')
            case self.open_kit_box:
                self.helper.click_at(self.helper.component_by_name('CraftBox'), By.CSS_SELECTOR, 'button#open_kit_box')
            case self.kit_box.create_new:
                self.helper.click_at(self.helper.component_by_name('KitBox'), By.CSS_SELECTOR, 'button#create_new')
            case _:
                raise ValueError(f'tool {tool} is not supported')

