"""The rules working together inside a Game, each switched on/off through a RuleSet."""
import pytest

from core import (
    Game, GameConfig, InvalidMoveError, MoveContext, Player, Position, Rule, RuleSet, players_for,
)
from tests.helpers import FixedCardSource, card

RED, BLUE = Player.RED, Player.BLUE
DOT = card((0, 0))
COLUMN = card((-1, 0), (0, 0), (1, 0))
FULL = card(*[(r, c) for r in (-1, 0, 1) for c in (-1, 0, 1)])  # all 9 cells
ROW5 = card(*[(0, c) for c in range(-2, 3)], size=5)  # a whole row of a 4-wide board


def make_game(cards, rules, **config):
    return Game(GameConfig(rules=rules, **config), FixedCardSource(*cards))


def small(cards, rules, turns=10):  # 3x3 board
    return make_game(cards, rules, board_size=3, total_turns=turns)


def row_game(cards, rules):  # 4x4 board; ROW5 played at (r, 1) paints the whole row r
    return make_game(cards, rules, board_size=4, card_size=5, colored_cells=5, total_turns=20)


# ---------------------------------------------------------------- no rules = plain game
def test_with_no_rules_nothing_special_ever_happens():
    game = small([FULL, COLUMN, COLUMN], RuleSet.none())
    result = game.play(Position(1, 1))  # fills the whole board and completes lines...
    assert result.events == () and not result.bonus_turn
    assert not game.is_over and game.current_player is BLUE
    assert game.rule_names == () and game.line_streak_limit is None


def test_each_rule_can_be_tested_alone():
    for name in ("line_bonus", "full_board_win", "line_streak_wipe", "catch_up_cards"):
        game = small([COLUMN, DOT], RuleSet.of(name))
        assert game.rule_names == (name,)
        game.play(Position(1, 1))  # nothing crashes whichever single rule is on


# ---------------------------------------------------------------- line_bonus
def test_line_bonus_gives_another_move_for_a_new_line_only():
    game = small([COLUMN], RuleSet.of("line_bonus"))
    first = game.play(Position(1, 1))
    assert first.bonus_turn and game.current_player is RED
    second = game.play(Position(1, 1))  # same line again: not new
    assert not second.bonus_turn and game.current_player is BLUE


def test_no_bonus_on_the_last_turn():
    game = small([COLUMN], RuleSet.of("line_bonus"), turns=1)
    assert not game.play(Position(1, 1)).bonus_turn and game.is_over


# ---------------------------------------------------------------- full_board_win
ROW0 = card((-1, -1), (-1, 0), (-1, 1))  # the top row of a 3x3 board, played at (1, 1)
ROW1 = card((0, -1), (0, 0), (0, 1))
ROW2 = card((1, -1), (1, 0), (1, 1))


def test_the_first_player_to_fill_the_grid_wins_immediately():
    game = small([FULL, DOT], RuleSet.of("full_board_win"))
    result = game.play(Position(1, 1))
    assert result.has_event("board_filled_win")
    assert game.is_over and game.winner() is RED
    assert game.turns_left == 9  # ended long before the turns ran out
    assert game.upcoming_cards == () and result.next_player is None
    with pytest.raises(InvalidMoveError):
        game.play(Position(0, 0))


def test_the_game_ends_when_the_grid_is_covered_by_both_players_and_the_score_decides():
    # RED paints the top row, BLUE the middle row, RED the last row -> covered by both
    game = small([ROW0, ROW1, ROW2], RuleSet.of("full_board_win"))
    game.play(Position(1, 1))
    game.play(Position(1, 1))
    result = game.play(Position(1, 1))
    assert game.is_over and result.has_event("board_filled_win")
    assert game.scores() == {RED: 6, BLUE: 3}
    assert game.winner() is RED and game.turns_left == 7


def behind_player_places_the_last_cell(rules):
    """RED paints rows 1-2 (6 cells), BLUE a dot then row 3: BLUE places the last cell with 3 vs 6."""
    game = small([ROW0, DOT, ROW1, ROW2], rules, turns=20)
    game.play(Position(1, 1))  # RED: top row
    game.play(Position(2, 2))  # BLUE: a single cell in the bottom-right corner
    game.play(Position(1, 1))  # RED: middle row -> RED 6, BLUE 1
    game.play(Position(1, 1))  # BLUE: bottom row -> the grid is covered, BLUE 3, RED 6
    return game


def test_a_player_who_places_the_last_cell_while_behind_loses_by_default():
    game = behind_player_places_the_last_cell(RuleSet.of("full_board_win"))
    assert game.is_over and game.scores() == {RED: 6, BLUE: 3}
    assert game.winner() is RED


def test_with_the_mover_option_that_player_wins_even_when_behind():
    rules = RuleSet.of("full_board_win").with_options("full_board_win", winner="mover")
    game = behind_player_places_the_last_cell(rules)
    assert game.is_over and game.scores() == {RED: 6, BLUE: 3}
    assert game.winner() is BLUE


def test_blue_can_win_by_filling_alone_too():
    game = small([DOT, FULL], RuleSet.of("full_board_win"))
    game.play(Position(0, 0))
    game.play(Position(1, 1))  # BLUE fills everything, overwriting RED
    assert game.winner() is BLUE and game.scores() == {RED: 0, BLUE: 9}


def test_a_partly_filled_grid_does_not_end_the_game():
    game = small([COLUMN], RuleSet.of("full_board_win"))
    game.play(Position(1, 1))
    assert not game.is_over


def test_without_the_rule_a_covered_grid_does_not_end_the_game():
    game = small([FULL, DOT], RuleSet.none())
    game.play(Position(1, 1))
    assert not game.is_over


# ---------------------------------------------------------------- full_board_flip
def test_flip_gives_the_board_to_the_opponent_who_plays():
    game = small([FULL, DOT], RuleSet.of("full_board_flip"))
    result = game.play(Position(1, 1))
    assert result.has_event("board_flipped") and not result.bonus_turn
    assert game.scores() == {RED: 0, BLUE: 9} and game.current_player is BLUE
    assert not game.is_over


def test_the_flipped_board_does_not_flip_back_on_a_move_that_changes_nothing():
    game = small([FULL, DOT], RuleSet.of("full_board_flip"))
    game.play(Position(1, 1))
    result = game.play(Position(0, 0))  # BLUE stamps a dot on its own cell
    assert result.events == () and game.current_player is RED
    assert game.scores()[BLUE] == 9


def test_flip_also_applies_on_the_last_turn():
    game = small([FULL], RuleSet.of("full_board_flip"), turns=1)
    game.play(Position(1, 1))
    assert game.is_over and game.winner() is BLUE


def test_when_both_full_board_rules_are_on_the_win_comes_first_and_flip_never_happens():
    game = small([FULL], RuleSet.of("full_board_win", "full_board_flip"))
    result = game.play(Position(1, 1))
    assert [e.code for e in result.events] == ["board_filled_win"]
    assert game.scores() == {RED: 9, BLUE: 0} and game.winner() is RED


# ---------------------------------------------------------------- line_streak_wipe
WIPE_AND_BONUS = RuleSet.of("line_streak_wipe", "line_bonus")


def test_three_line_moves_in_a_row_wipe_your_cells_but_not_the_opponents():
    game = row_game([DOT, DOT, ROW5, ROW5, ROW5], WIPE_AND_BONUS)
    game.play(Position(3, 0))  # RED
    game.play(Position(3, 3))  # BLUE
    first = game.play(Position(0, 1))
    second = game.play(Position(1, 1))
    assert first.bonus_turn and first.line_streak == 1
    assert second.bonus_turn and second.line_streak == 2
    assert game.line_streak == 2 and game.line_streak_limit == 3

    third = game.play(Position(2, 1))
    assert third.has_event("cells_wiped") and not third.bonus_turn  # no bonus after a wipe
    assert game.scores() == {RED: 0, BLUE: 1}
    assert game.grid[3][3] is BLUE and game.current_player is BLUE
    assert game.line_streak == 0


def test_a_move_without_a_new_line_resets_the_streak():
    game = row_game([ROW5, ROW5, DOT, ROW5, ROW5, ROW5], WIPE_AND_BONUS)
    game.play(Position(0, 1))
    game.play(Position(1, 1))
    assert game.line_streak == 2
    result = game.play(Position(0, 0))
    assert result.line_streak == 0 and game.current_player is BLUE


def test_the_streak_limit_is_an_option_and_the_rule_can_be_off():
    game = row_game([ROW5, ROW5], WIPE_AND_BONUS.with_options("line_streak_wipe", limit=2))
    game.play(Position(0, 1))
    assert game.play(Position(1, 1)).has_event("cells_wiped")

    game = row_game([ROW5, ROW5, ROW5], RuleSet.of("line_bonus"))
    for row in range(3):
        assert not game.play(Position(row, 1)).has_event("cells_wiped")
    assert game.scores()[RED] == 12 and game.line_streak_limit is None


def test_if_two_penalties_happen_together_the_first_in_the_order_wins():
    rules = RuleSet.of("full_board_flip", "line_streak_wipe", "line_bonus")
    game = small([COLUMN, COLUMN, COLUMN], rules)
    game.play(Position(1, 0))
    game.play(Position(1, 1))
    result = game.play(Position(1, 2))  # 3rd line AND the whole board is RED
    assert [e.code for e in result.events] == ["board_flipped"]
    assert game.scores() == {RED: 0, BLUE: 9}


# ---------------------------------------------------------------- catch_up_cards
BASE_FOR_BLUE = card((-1, 0), (0, 1), (1, -1), (1, 1))  # no line
BASE_FOR_RED = card((0, 0), (0, 1), (1, 0), (1, 1))  # colored center, no line


def catch_up_game(gap=2):
    rules = RuleSet.of("catch_up_cards").with_options("catch_up_cards", gap=gap)
    return make_game([FULL, BASE_FOR_BLUE, BASE_FOR_RED], rules, total_turns=20)


def test_the_trailing_player_gets_a_line_card_and_the_leader_a_neutral_center_card():
    game = catch_up_game()
    game.play(Position(1, 1))  # RED paints 9 cells: RED 9 - BLUE 0
    assert game.current_player is BLUE
    boosted = game.current_card
    assert boosted.has_line() and len(boosted.offsets) == 4 and "boost" in boosted.note.lower()
    assert game.upcoming_cards[0] == BASE_FOR_RED  # previews are shown as drawn

    game.play(Position(3, 3))  # BLUE paints 4 cells far from RED: RED 9 - BLUE 4
    assert game.current_player is RED
    handicapped = game.current_card
    assert Position(0, 0) not in handicapped.offsets and len(handicapped.offsets) == 4
    assert "handicap" in handicapped.note.lower()


def test_cards_are_untouched_when_the_difference_is_within_the_gap():
    game = catch_up_game(gap=10)
    game.play(Position(1, 1))  # 9 - 0 is not more than 10
    assert game.current_card.offsets == BASE_FOR_BLUE.offsets and game.current_card.note == ""


def test_cards_are_untouched_when_the_rule_is_off():
    rules = RuleSet.none()
    game = make_game([FULL, BASE_FOR_BLUE, BASE_FOR_RED], rules, total_turns=20)
    game.play(Position(1, 1))
    assert game.current_card.offsets == BASE_FOR_BLUE.offsets


def test_the_player_who_keeps_the_turn_gets_a_card_for_the_new_scores():
    rules = RuleSet.of("line_bonus", "catch_up_cards").with_options("catch_up_cards", gap=2)
    game = make_game([COLUMN, BASE_FOR_RED, BASE_FOR_RED], rules, board_size=3, total_turns=20)
    game.play(Position(1, 1))  # RED completes a line: bonus; RED now leads 3-0
    assert game.current_player is RED
    assert Position(0, 0) not in game.current_card.offsets  # handicapped as the leader


# ---------------------------------------------------------------- the engine itself
def test_rules_run_in_order_and_stop_as_soon_as_one_decides():
    calls = []

    class Decider(Rule):
        name = "decider"
        description = "decides"

        def after_move(self, ctx: MoveContext) -> None:
            calls.append("decider")
            ctx.pass_turn()

    class Later(Rule):
        name = "later"
        description = "never reached"

        def after_move(self, ctx: MoveContext) -> None:
            calls.append("later")

    game = Game(GameConfig(), FixedCardSource(DOT), rules=[Decider(), Later()])
    game.play(Position(0, 0))
    assert calls == ["decider"] and game.rule_names == ("decider", "later")
    game.play(Position(1, 1))
    assert calls == ["decider", "decider"]


def test_a_rule_can_end_the_game_and_let_the_score_decide():
    class Stop(Rule):
        name = "stop"
        description = "ends the game after every move"

        def after_move(self, ctx: MoveContext) -> None:
            ctx.end_game()

    game = Game(GameConfig(), FixedCardSource(DOT), rules=[Stop()])
    game.play(Position(0, 0))
    assert game.is_over and game.winner() is RED and game.scores()[RED] == 1


# ---------------------------------------------------------------- upcoming cards
def test_current_and_next_two_cards_are_visible_and_shift_each_turn():
    a, b, c, d = card((0, 0)), card((1, 0)), card((0, 1)), card((-1, 0))
    game = make_game([a, b, c, d], RuleSet.none())
    assert game.current_card == a and game.upcoming_cards == (b, c)
    game.play(Position(2, 2))
    assert game.current_card == b and game.upcoming_cards == (c, d)


def test_upcoming_cards_are_only_the_ones_that_will_really_be_played():
    cards = [card((0, 0)), card((1, 0)), card((0, 1))]
    assert make_game(cards, RuleSet.none(), total_turns=2).upcoming_cards == (cards[1],)
    assert make_game(cards, RuleSet.none(), total_turns=1).upcoming_cards == ()


def test_preview_can_be_changed_or_disabled():
    cards = [card((0, 0)), card((1, 0)), card((0, 1)), card((-1, 0))]
    assert len(make_game(cards, RuleSet.none(), preview_cards=3).upcoming_cards) == 3
    zero = make_game(cards, RuleSet.none(), preview_cards=0)
    assert zero.upcoming_cards == ()
    zero.play(Position(2, 2))
    assert zero.current_card == cards[1]


# ---------------------------------------------------------------- every combination of switches
def test_every_on_off_combination_plays_random_games_without_problems():
    import itertools
    import random

    from core import RandomCardSource
    from core.rules import RULES

    names = [rule.name for rule in RULES]
    for flags in itertools.product([False, True], repeat=len(names)):
        rules = RuleSet.of(*[n for n, on in zip(names, flags) if on])
        for seed in range(6):
            rng = random.Random(seed)
            config = GameConfig(rules=rules)
            game = Game(config, RandomCardSource.from_config(config, rng))
            moves = 0
            while not game.is_over:
                result = game.play(Position(rng.randrange(5), rng.randrange(5)))
                moves += 1
                assert moves <= config.total_turns
                assert len(game.current_card.offsets) == config.colored_cells
                assert result.bonus_turn == (not game.is_over and game.current_player is result.player)
            assert game.turns_played == moves
            scores = game.scores()
            assert sum(scores.values()) <= 25
            if "full_board_win" not in rules.names:
                assert moves == config.total_turns  # only that rule can end a game early
            assert game.winner() in (RED, BLUE, None)


# ---------------------------------------------------------------- several players
GREEN, YELLOW = Player.GREEN, Player.YELLOW


def multi(cards, rules, count=3, turns=30, **config):
    return Game(
        GameConfig(players=players_for(count), rules=rules, total_turns=turns, **config),
        FixedCardSource(*cards),
    )


def test_players_take_turns_in_the_order_of_the_config_and_wrap_around():
    game = multi([DOT], RuleSet.none(), count=3)
    order = []
    for i in range(7):
        order.append(game.current_player)
        result = game.play(Position(i % 5, 0))
        assert result.next_player is game.current_player
    assert order == [RED, BLUE, GREEN, RED, BLUE, GREEN, RED]
    assert game.players == (RED, BLUE, GREEN)


def test_a_bonus_turn_keeps_the_same_player_in_a_multi_player_game():
    game = Game(
        GameConfig(players=players_for(3), rules=RuleSet.of("line_bonus"), board_size=3, total_turns=20),
        FixedCardSource(COLUMN),
    )
    result = game.play(Position(1, 1))
    assert result.bonus_turn and result.next_player is RED and game.current_player is RED
    game.play(Position(1, 1))  # no new line
    assert game.current_player is BLUE


def test_a_player_with_a_new_color_can_overwrite_and_be_overwritten():
    game = multi([DOT], RuleSet.none(), count=3)
    game.play(Position(2, 2))  # RED
    game.play(Position(2, 2))  # BLUE overwrites RED
    game.play(Position(2, 2))  # GREEN overwrites BLUE
    assert game.scores() == {RED: 0, BLUE: 0, GREEN: 1}


def test_the_ranking_handles_ties_between_several_players():
    game = multi([DOT], RuleSet.none(), count=3, turns=3)
    for row in range(3):
        game.play(Position(row, 0))  # one cell each
    assert game.is_over and set(game.winners()) == {RED, BLUE, GREEN} and game.winner() is None

    game = multi([DOT], RuleSet.none(), count=3, turns=4)
    for row in range(4):
        game.play(Position(row, 0))  # RED, BLUE, GREEN, then RED again -> RED 2, BLUE 1, GREEN 1
    assert game.winners() == (RED,) and game.winner() is RED


def test_two_of_three_players_can_tie_for_the_win():
    game = multi([DOT], RuleSet.none(), count=3, turns=5)
    for position in [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]:
        game.play(Position(*position))  # RED 2, BLUE 2, GREEN 1
    assert game.winners() == (RED, BLUE) and game.winner() is None


def test_filling_the_grid_with_several_players_ends_the_game_for_everybody():
    # RED, BLUE and GREEN each paint a row of a 3x3 board
    game = Game(
        GameConfig(players=players_for(3), rules=RuleSet.of("full_board_win"), board_size=3, total_turns=30),
        FixedCardSource(ROW0, ROW1, ROW2),
    )
    for _ in range(3):
        game.play(Position(1, 1))
    assert game.is_over and game.turns_left == 27
    assert game.scores() == {RED: 3, BLUE: 3, GREEN: 3} and game.winner() is None


def test_flip_gives_the_board_to_the_next_player_in_turn_order():
    game = Game(
        GameConfig(players=players_for(3), rules=RuleSet.of("full_board_flip"), board_size=3, total_turns=20),
        FixedCardSource(DOT, FULL, DOT),
    )
    game.play(Position(0, 0))  # RED
    result = game.play(Position(1, 1))  # BLUE fills the whole board -> goes to GREEN, GREEN plays
    assert result.has_event("board_flipped") and result.next_player is GREEN
    assert game.scores() == {RED: 0, BLUE: 0, GREEN: 9} and game.current_player is GREEN
