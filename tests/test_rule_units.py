"""Each rule tested ALONE: a hand-made context, no Game involved."""
import pytest

from core import (
    Board, CardContext, CatchUpCards, FullBoardFlip, FullBoardWin, LineBonus,
    LineStreakWipe, MoveContext, Player, Position, Rule,
)
from tests.helpers import card

RED, BLUE = Player.RED, Player.BLUE
P = Position


PLAYERS = (RED, BLUE)


def ctx(board=None, player=RED, changed=(P(0, 0),), new_lines=(), line_streak=0, turns_left=10,
        players=PLAYERS):
    index = players.index(player)
    return MoveContext(
        board=board or Board(3), player=player, next_player=players[(index + 1) % len(players)],
        players=players, changed=changed, new_lines=new_lines, line_streak=line_streak,
        turns_left=turns_left,
    )


def full_board(owner):
    board = Board(3)
    board.paint([P(r, c) for r in range(3) for c in range(3)], owner)
    return board


# ---------------------------------------------------------------- line_bonus
def test_line_bonus_grants_another_move_for_a_new_line():
    c = ctx(new_lines=("row 1",))
    LineBonus().after_move(c)
    assert c.bonus_turn and not c.decided
    assert c.events[0].code == "line_bonus" and "row 1" in c.events[0].text


def test_line_bonus_does_nothing_without_a_new_line():
    c = ctx()
    LineBonus().after_move(c)
    assert not c.bonus_turn and c.events == []


def test_line_bonus_is_not_given_on_the_last_turn():
    c = ctx(new_lines=("row 1",), turns_left=0)
    LineBonus().after_move(c)
    assert not c.bonus_turn


# ---------------------------------------------------------------- line_streak_wipe
def test_wipe_removes_only_the_movers_cells_and_passes_the_turn():
    board = Board(3)
    board.paint([P(0, 0), P(1, 1)], RED)
    board.paint([P(2, 2)], BLUE)
    c = ctx(board=board, line_streak=3)
    LineStreakWipe().after_move(c)
    assert board.count(RED) == 0 and board.count(BLUE) == 1
    assert c.decided and not c.bonus_turn and not c.game_ended
    assert c.events[0].code == "cells_wiped"


def test_wipe_waits_for_the_limit_and_the_limit_is_an_option():
    board = Board(3)
    board.paint([P(0, 0)], RED)
    below = ctx(board=board, line_streak=2)
    LineStreakWipe().after_move(below)
    assert not below.decided and board.count(RED) == 1

    at_two = ctx(board=board, line_streak=2)
    LineStreakWipe(limit=2).after_move(at_two)
    assert at_two.decided and board.count(RED) == 0


def test_unknown_rule_option_is_rejected():
    with pytest.raises(ValueError, match="no option"):
        LineStreakWipe(speed=3)


# ---------------------------------------------------------------- full_board_flip
def test_flip_gives_the_whole_board_to_the_next_player():
    board = full_board(RED)
    c = ctx(board=board)
    FullBoardFlip().after_move(c)
    assert board.is_filled_with(BLUE)
    assert c.decided and not c.bonus_turn and not c.game_ended
    assert c.events[0].code == "board_flipped"


def test_with_three_players_the_board_goes_to_the_next_one_in_turn_order():
    players = (RED, BLUE, Player.GREEN)
    board = full_board(BLUE)
    FullBoardFlip().after_move(ctx(board=board, player=BLUE, players=players))
    assert board.is_filled_with(Player.GREEN)
    wrap = full_board(Player.GREEN)
    FullBoardFlip().after_move(ctx(board=wrap, player=Player.GREEN, players=players))
    assert wrap.is_filled_with(RED)  # turn order wraps around


def test_flip_needs_a_move_that_changed_something_and_a_full_board():
    unchanged = ctx(board=full_board(RED), changed=())
    FullBoardFlip().after_move(unchanged)
    assert not unchanged.decided

    partial = Board(3)
    partial.paint([P(0, 0)], RED)
    c = ctx(board=partial)
    FullBoardFlip().after_move(c)
    assert not c.decided and partial.count(RED) == 1


def test_flip_is_off_by_default():
    assert FullBoardFlip.enabled_by_default is False


# ---------------------------------------------------------------- full_board_win
def mixed_full_board():
    """Every cell is owned, but by both players (RED 6, BLUE 3)."""
    board = full_board(RED)
    board.paint([P(2, 0), P(2, 1), P(2, 2)], BLUE)
    return board


def test_filling_the_grid_alone_ends_the_game_and_wins():
    c = ctx(board=full_board(BLUE), player=BLUE)
    FullBoardWin().after_move(c)
    assert c.game_ended and c.winner is BLUE and c.decided
    assert c.events[0].code == "board_filled_win" and "wins immediately" in c.events[0].text


def test_a_grid_covered_by_several_players_also_ends_the_game_and_the_score_decides():
    c = ctx(board=mixed_full_board(), player=BLUE)  # BLUE (the minority) placed the last cell
    FullBoardWin().after_move(c)
    assert c.game_ended and c.decided
    assert c.winner is None  # no forced winner: the player with the most cells wins
    assert c.events[0].code == "board_filled_win"


def test_the_winner_option_can_make_the_player_who_filled_the_last_cell_win():
    c = ctx(board=mixed_full_board(), player=BLUE)
    FullBoardWin(winner="mover").after_move(c)
    assert c.game_ended and c.winner is BLUE


def test_win_option_is_validated():
    with pytest.raises(ValueError, match="one of"):
        FullBoardWin(winner="nobody")


def test_the_game_goes_on_while_a_cell_is_still_neutral():
    partial = Board(3)
    partial.paint([P(r, c) for r in range(3) for c in range(3) if (r, c) != (2, 2)], RED)  # 8 of 9
    c = ctx(board=partial)
    FullBoardWin().after_move(c)
    assert not c.game_ended and not c.decided and c.events == []


# ---------------------------------------------------------------- catch_up_cards
NO_LINE = card((-1, 0), (0, 1), (1, -1), (1, 1))
CENTER_ON = card((0, 0), (0, 1), (1, 0), (1, 1))


def cards_ctx(red, blue, player=RED):
    return CardContext(player, {RED: red, BLUE: blue}, PLAYERS)


def test_nothing_changes_when_the_difference_is_not_more_than_the_gap():
    rule = CatchUpCards()
    for red, blue in [(0, 0), (15, 5), (5, 15)]:  # difference of exactly 10 is NOT "more than 10"
        assert rule.adjust_card(NO_LINE, cards_ctx(red, blue)).offsets == NO_LINE.offsets
        assert rule.adjust_card(NO_LINE, cards_ctx(red, blue)).note == ""


def test_the_trailing_player_gets_a_card_with_a_full_line_and_still_4_cells():
    boosted = CatchUpCards().adjust_card(NO_LINE, cards_ctx(red=3, blue=14))
    assert boosted.has_line() and len(boosted.offsets) == 4
    assert "boost" in boosted.note.lower()


def test_the_leader_gets_a_card_with_a_neutral_center_and_still_4_cells():
    handicapped = CatchUpCards().adjust_card(CENTER_ON, cards_ctx(red=14, blue=3))
    assert P(0, 0) not in handicapped.offsets and len(handicapped.offsets) == 4
    assert "handicap" in handicapped.note.lower()


def test_it_depends_on_who_plays_the_card():
    rule = CatchUpCards()
    scores = {RED: 20, BLUE: 2}
    red_card = rule.adjust_card(CENTER_ON, CardContext(RED, scores, PLAYERS))  # RED leads
    blue_card = rule.adjust_card(NO_LINE, CardContext(BLUE, scores, PLAYERS))  # BLUE trails
    assert P(0, 0) not in red_card.offsets
    assert blue_card.has_line()


def test_the_gap_is_an_option():
    rule = CatchUpCards(gap=2)
    assert rule.adjust_card(NO_LINE, cards_ctx(red=0, blue=3)).has_line()


def test_with_several_players_each_is_compared_with_the_best_of_the_others():
    rule = CatchUpCards()
    G = Player.GREEN
    players = (RED, BLUE, G)
    scores = {RED: 30, BLUE: 12, G: 3}
    # GREEN is 27 behind the best other player: boost. BLUE is 18 behind RED: boost too.
    assert rule.adjust_card(NO_LINE, CardContext(G, scores, players)).has_line()
    assert rule.adjust_card(NO_LINE, CardContext(BLUE, scores, players)).has_line()
    # RED leads the best other player (BLUE) by 18: handicap.
    assert P(0, 0) not in rule.adjust_card(CENTER_ON, CardContext(RED, scores, players)).offsets


def test_the_leader_is_only_handicapped_if_it_leads_everybody_by_more_than_the_gap():
    rule = CatchUpCards()
    G = Player.GREEN
    players = (RED, BLUE, G)
    close_second = {RED: 30, BLUE: 25, G: 0}  # BLUE is only 5 behind RED
    untouched = rule.adjust_card(CENTER_ON, CardContext(RED, close_second, players))
    assert untouched.offsets == CENTER_ON.offsets and untouched.note == ""


# ---------------------------------------------------------------- the base class
def test_a_rule_that_overrides_nothing_changes_nothing():
    class Nothing(Rule):
        name = "nothing"
        description = "does nothing"

    c = ctx()
    Nothing().after_move(c)
    assert c.events == [] and not c.decided and not c.bonus_turn
    assert Nothing().adjust_card(NO_LINE, cards_ctx(0, 0)) is NO_LINE
