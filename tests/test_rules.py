"""The three 'big' rules: upcoming cards, full-board flip, line-streak wipe."""
from core import Game, GameConfig, Player, Position
from tests.helpers import FixedCardSource, card

DOT = card((0, 0))
COLUMN = card((-1, 0), (0, 0), (1, 0))
FULL = card(*[(r, c) for r in (-1, 0, 1) for c in (-1, 0, 1)])  # all 9 cells
ROW5 = card(*[(0, c) for c in range(-2, 3)], size=5)  # a whole row of a 4-wide board


def make_game(cards, **config):
    return Game(GameConfig(**config), FixedCardSource(*cards))


def row_game(cards, **config):
    """4x4 board, 5x5 cards: ROW5 played at (r, 1) paints the whole row r."""
    return make_game(cards, board_size=4, card_size=5, colored_cells=5,
                     total_turns=20, **config)


# ---------------------------------------------------------------- upcoming cards
def test_current_and_next_two_cards_are_visible_and_shift_each_turn():
    a, b, c, d = (card((0, 0)), card((1, 0)), card((0, 1)), card((-1, 0)))
    game = make_game([a, b, c, d])
    assert game.current_card == a and game.upcoming_cards == (b, c)
    game.play(Position(2, 2))
    assert game.current_card == b and game.upcoming_cards == (c, d)


def test_upcoming_cards_are_only_the_ones_that_will_really_be_played():
    a, b, c = card((0, 0)), card((1, 0)), card((0, 1))
    assert make_game([a, b, c], total_turns=2).upcoming_cards == (b,)
    assert make_game([a, b, c], total_turns=1).upcoming_cards == ()
    game = make_game([a, b, c], total_turns=2)
    game.play(Position(0, 0))
    game.play(Position(1, 1))
    assert game.upcoming_cards == ()  # game over


def test_preview_can_be_changed_or_disabled():
    cards = [card((0, 0)), card((1, 0)), card((0, 1)), card((-1, 0))]
    assert len(make_game(cards, preview_cards=3).upcoming_cards) == 3
    assert make_game(cards, preview_cards=0).upcoming_cards == ()


# ---------------------------------------------------------------- full board -> opponent
def test_filling_the_whole_board_gives_it_to_the_opponent_who_plays():
    game = make_game([FULL, DOT], board_size=3, total_turns=10)
    result = game.play(Position(1, 1))
    assert result.board_flipped and not result.bonus_turn
    assert all(cell is Player.BLUE for row in game.grid for cell in row)
    assert game.current_player is Player.BLUE
    assert game.scores() == {Player.RED: 0, Player.BLUE: 9}


def test_the_flipped_board_does_not_flip_back_on_a_move_that_changes_nothing():
    game = make_game([FULL, DOT], board_size=3, total_turns=10)
    game.play(Position(1, 1))  # RED fills it -> all BLUE, BLUE to play
    result = game.play(Position(0, 0))  # BLUE stamps a dot on its own cell
    assert not result.board_flipped and result.changed_cells == ()
    assert game.current_player is Player.RED  # no bonus either
    assert game.scores()[Player.BLUE] == 9


def test_flip_can_be_disabled():
    game = make_game([FULL, DOT], board_size=3, total_turns=10, full_board_flip=False)
    result = game.play(Position(1, 1))
    assert not result.board_flipped and result.bonus_turn
    assert game.scores()[Player.RED] == 9 and game.current_player is Player.RED


def test_flip_also_applies_on_the_last_turn():
    game = make_game([FULL], board_size=3, total_turns=1)
    game.play(Position(1, 1))
    assert game.is_over and game.winner() is Player.BLUE


# ---------------------------------------------------------------- 3 lines in a row -> wipe
def test_three_line_moves_in_a_row_wipe_all_your_cells_but_not_the_opponents():
    # RED dot, BLUE dot, then RED completes rows 1, 2 and 3 on three consecutive moves
    game = row_game([DOT, DOT, ROW5, ROW5, ROW5])
    game.play(Position(3, 0))  # RED
    game.play(Position(3, 3))  # BLUE
    first = game.play(Position(0, 1))
    second = game.play(Position(1, 1))
    assert first.bonus_turn and first.line_streak == 1
    assert second.bonus_turn and second.line_streak == 2
    assert game.current_player is Player.RED

    third = game.play(Position(2, 1))
    assert third.cells_wiped and not third.bonus_turn
    assert game.scores() == {Player.RED: 0, Player.BLUE: 1}
    assert game.grid[3][3] is Player.BLUE  # the opponent's cell is untouched
    assert game.current_player is Player.BLUE
    assert game.line_streak == 0


def test_a_move_without_a_new_line_resets_the_streak():
    game = row_game([ROW5, ROW5, DOT, ROW5, ROW5, ROW5])
    game.play(Position(0, 1))
    game.play(Position(1, 1))
    assert game.line_streak == 2
    result = game.play(Position(0, 0))  # no new line
    assert result.line_streak == 0 and game.line_streak == 0
    assert game.current_player is Player.BLUE


def test_streak_limit_is_configurable_and_can_be_disabled():
    game = row_game([ROW5, ROW5], line_streak_limit=2)
    game.play(Position(0, 1))
    assert game.play(Position(1, 1)).cells_wiped

    game = row_game([ROW5, ROW5, ROW5], line_streak_limit=None)
    for row in range(3):
        result = game.play(Position(row, 1))
        assert not result.cells_wiped
    assert game.scores()[Player.RED] == 12


def test_if_both_penalties_happen_together_the_board_flip_wins():
    game = make_game([COLUMN, COLUMN, COLUMN], board_size=3, total_turns=10)
    game.play(Position(1, 0))
    game.play(Position(1, 1))
    result = game.play(Position(1, 2))  # 3rd line AND the whole board is RED
    assert result.board_flipped and not result.cells_wiped
    assert game.scores() == {Player.RED: 0, Player.BLUE: 9}
