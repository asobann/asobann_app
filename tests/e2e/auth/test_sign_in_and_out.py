import pytest
from selenium import webdriver
from ..helper import GameHelper


def sign_in(host, registered_user):
    host.menu.sign_in.click()
    # enter email
    # enter password


@pytest.mark.usefixtures("server")
class TestSignInAndOut:
    def test_not_signed_in(self, browser: webdriver.Firefox):
        host = GameHelper.player(browser)

        assert host.menu.sign_in.is_visible()
        assert not host.menu.sign_out.is_visible()

    def test_signing_in(self, browser: webdriver.Firefox, registered_user):
        host = GameHelper.player(browser)
        sign_in(host, registered_user)

        assert host.should_not_have_text('You are host')
        assert host.should_have_text(registered_user.nickname)

    def test_signed_in(self, browser: webdriver.Firefox, registered_user):
        host = GameHelper.player(browser)
        sign_in(host, registered_user)

        assert not host.menu.sign_in.is_visible()
        assert host.menu.sign_out.is_visible()

    def test_signing_out(self, browser: webdriver.Firefox, registered_user):
        host = GameHelper.player(browser)
        sign_in(host, registered_user)

        host.menu.sign_out.click()

        assert host.menu.sign_in.is_visible()
        assert not host.menu.sign_out.is_visible()


@pytest.mark.usefixtures("server")
class TestPlayerName:
    class TestYouAreHost:
        def test_nickname_is_used(self, browser: webdriver.Firefox, registered_user):
            host = GameHelper.player(browser)
            sign_in(host, registered_user)

            assert host.should_not_have_text('You are host')

    class TestYouAreVisitor:
        def test_name_is_filled_with_nickname(self, browser: webdriver.Firefox,
                                              another_browser: webdriver.Firefox, registered_user):
            host = GameHelper.player(browser)
            another = GameHelper(another_browser)
            sign_in(another, registered_user)
            another.go(host.current_url)

            another.menu.join("Player 2")
            input_element = another.browser.find_element_by_css_selector("input#player_name")
            assert input_element.text == registered_user.nickname
