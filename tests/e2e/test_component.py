import pytest
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from selenium.common.exceptions import NoSuchElementException

from .helper import compo_pos, Rect, GameHelper, TOP


C_A = 'PlayingCard S_A'
C_K = 'PlayingCard S_K'
C_Q = 'PlayingCard S_Q'


@pytest.mark.usefixtures("server")
class TestHandArea:
    def put_one_card_each_on_2_hand_areas(self, host, another):
        host.go(TOP)
        host.should_have_text("you are host")

        host.menu.add_my_hand_area.click()
        host.move_card_to_hand_area(host.component_by_name(C_A), 'host', (-100, 0))

        another.go(host.current_url)
        another.menu.join("Player 2")
        another.should_have_text("you are Player 2")

        another.menu.add_my_hand_area.click()
        another.move_card_to_hand_area(another.component_by_name(C_K), 'Player 2', (100, 0))

        host.double_click(host.component_by_name(C_A))
        another.double_click(another.component_by_name(C_K))

    def test_cards_in_hand_are_looks_facedown(self, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
        host = GameHelper(browser)
        another = GameHelper(another_browser)
        self.put_one_card_each_on_2_hand_areas(host, another)

        # assert text
        assert '♠A' in host.component_by_name(C_A).face()
        assert '♠A' not in another.component_by_name(C_A).face()
        assert '♠K' not in host.component_by_name(C_K).face()
        assert '♠K' in another.component_by_name(C_K).face()

        # assert image
        assert 'card_up.png' in host.component_by_name(C_A).face()
        assert 'card_back.png' in another.component_by_name(C_A).face()
        assert 'card_back.png' in host.component_by_name(C_K).face()
        assert 'card_up.png' in another.component_by_name(C_K).face()

    def test_cannot_handle_cards_owned_by_someone_else(self, browser: webdriver.Firefox,
                                                       another_browser: webdriver.Firefox):
        host = GameHelper(browser)
        another = GameHelper(another_browser)
        self.put_one_card_each_on_2_hand_areas(host, another)

        # cannot move
        before = host.component_by_name(C_K).rect()
        host.drag(host.component_by_name(C_K), 20, 0)
        assert before == host.component_by_name(C_K).rect()

        before = another.component_by_name(C_A).rect()
        another.drag(another.component_by_name(C_A), 20, 0)
        assert before == another.component_by_name(C_A).rect()

        # cannot flip
        face = host.component_by_name(C_K).face()
        host.double_click(host.component_by_name(C_K))
        assert face == host.component_by_name(C_K).face()

        face = another.component_by_name(C_A).face()
        another.double_click(another.component_by_name(C_A))
        assert face == another.component_by_name(C_A).face()

    def test_up_card_in_my_hand_become_down_when_moved_to_others_hand(self, browser: webdriver.Firefox,
                                                                      another_browser: webdriver.Firefox):
        host = GameHelper(browser)
        another = GameHelper(another_browser)
        self.put_one_card_each_on_2_hand_areas(host, another)

        host.move_card_to_hand_area(host.component_by_name(C_A), 'Player 2')
        another.move_card_to_hand_area(another.component_by_name(C_K), 'host')

        # assert text
        assert '♠A' not in host.component_by_name(C_A).face()
        assert '♠A' in another.component_by_name(C_A).face()
        assert '♠K' in host.component_by_name(C_K).face()
        assert '♠K' not in another.component_by_name(C_K).face()

        # assert image
        assert 'card_back.png' in host.component_by_name(C_A).face()
        assert 'card_up.png' in another.component_by_name(C_A).face()
        assert 'card_up.png' in host.component_by_name(C_K).face()
        assert 'card_back.png' in another.component_by_name(C_K).face()

    def test_cards_on_hand_area_follows_when_hand_area_is_moved(self, browser: webdriver.Firefox,
                                                               another_browser: webdriver.Firefox):
        host = GameHelper(browser)
        another = GameHelper(another_browser)
        self.put_one_card_each_on_2_hand_areas(host, another)

        host_card = host.component_by_name(C_A)
        host_card_pos = host_card.pos()
        hand_area = host.hand_area(owner="host")
        host.drag(hand_area, -50, -100)
        assert host_card_pos.left - 50 == host_card.pos().left
        assert host_card_pos.top - 100 == host_card.pos().top

        # host_card is still owned by host
        assert '♠A' in host.component_by_name(C_A).face()
        assert '♠A' not in another.component_by_name(C_A).face()

        host.double_click(host_card)
        assert '♠A' not in host.component_by_name(C_A).face()
        assert '♠A' not in another.component_by_name(C_A).face()

        host.double_click(host_card)
        assert '♠A' in host.component_by_name(C_A).face()
        assert '♠A' not in another.component_by_name(C_A).face()

    def test_many_cards_on_hand_area_move_with_the_area(self, browser: webdriver.Firefox,
                                                        another_browser: webdriver.Firefox):
        host = GameHelper(browser)
        another = GameHelper(another_browser)

        host.go(TOP)
        host.should_have_text("you are host")
        another.go(host.current_url)
        another.menu.join("Player 2")
        another.should_have_text("you are Player 2")

        host.menu.add_my_hand_area.click()
        c1, c2, c3 = "PlayingCard S_A", "PlayingCard S_K", "PlayingCard S_Q"
        host.move_card_to_hand_area(host.component_by_name(c1), 'host', (-100, 10))
        host.move_card_to_hand_area(host.component_by_name(c2), 'host', (0, 0))
        host.move_card_to_hand_area(host.component_by_name(c3), 'host', (75, -10))

        pos_before = [host.component_by_name(c).pos() for c in (c1, c2, c3)]
        host.drag(host.hand_area(owner="host"), 200, 300, grab_at=(-40, 0))
        pos_after = [host.component_by_name(c).pos() for c in (c1, c2, c3)]

        assert pos_before[0].left + 200 == pos_after[0].left and pos_before[0].top + 300 == pos_after[0].top
        assert pos_before[1].left + 200 == pos_after[1].left and pos_before[1].top + 300 == pos_after[1].top
        assert pos_before[2].left + 200 == pos_after[2].left and pos_before[2].top + 300 == pos_after[2].top

        pos_another = [another.component_by_name(c).pos() for c in (c1, c2, c3)]
        assert pos_after == pos_another


    def test_resizing_hand_area_updates_ownership(self, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
        host = GameHelper(browser)
        another = GameHelper(another_browser)
        self.put_one_card_each_on_2_hand_areas(host, another)

        host.double_click(host.component_by_name(C_Q))
        time.sleep(0.1)  # prevent unintended double clicking
        host.move_card_to_hand_area(host.component_by_name(C_Q), 'host', (0, -100))  # just outside

        hand_area = host.hand_area(owner="host")
        host.drag(hand_area, 0, -100, 'top')
        host.drag(hand_area, 0, -100, 'bottom')

        # host_card is no longer owned by host
        assert '♠A' in another.component_by_name(C_A).face()

        # PlayingCard S_3 is owned by host
        assert '♠Q' in host.component_by_name(C_Q).face()
        assert '♠Q' not in another.component_by_name(C_Q).face()

    def test_cards_on_hand_area_have_visible_clue(self, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
        host = GameHelper(browser)
        another = GameHelper(another_browser)

        self.put_one_card_each_on_2_hand_areas(host, another)
        assert host.component_by_name(C_A).owner()
        assert host.component_by_name(C_K).owner()
        assert not host.component_by_name('PlayingCard H_A').owner()

    def test_removing_hand_area(self, browser: webdriver.Firefox, another_browser: webdriver.Firefox):
        host = GameHelper(browser)
        another = GameHelper(another_browser)
        self.put_one_card_each_on_2_hand_areas(host, another)

        host.menu.remove_my_hand_area.click()
        another.menu.remove_my_hand_area.click()

        assert not host.component_by_name(C_A).owner()
        assert not host.component_by_name(C_K).owner()
        assert not another.component_by_name(C_A).owner()
        assert not another.component_by_name(C_K).owner()



@pytest.mark.usefixtures("server")
class TestDice:
    def test_add_dice_from_menu(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        host.go(TOP)
        host.should_have_text("you are host")

        host.menu.add_component.execute()
        host.menu.add_component_from_list("Dice (Blue)")

        assert host.component_by_name("Dice (Blue)")
        assert host.component_by_name("Dice (Blue)").rect().height == 66
        assert host.component_by_name("Dice (Blue)").rect().width == 66

    def test_show_number_of_dices_on_the_table(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        host.go(TOP)
        host.should_have_text("you are host")
        host.menu.add_component.execute()

        host.menu.add_component_from_list("Dice (Blue)")
        host.should_have_text("1 on the table")

        host.menu.add_component_from_list("Dice (Blue)")
        host.should_have_text("2 on the table")

    @pytest.mark.skip
    def test_add_by_dragging(self, browser: webdriver.Firefox):
        pass

    @pytest.mark.skip
    def test_roll(self, browser: webdriver.Firefox):
        pass

    def test_remove_dice_from_table(self, browser: webdriver.Firefox):
        host = GameHelper(browser)
        host.go(TOP)
        host.menu.add_component.execute()
        host.menu.add_component_from_list("Dice (Blue)")

        host.menu.remove_component_from_list("Dice (Blue)")
        host.should_not_see_component("Dice (Blue)")
