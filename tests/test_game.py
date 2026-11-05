import pytest

from core import Game, GameConfig, InvalidMoveError, Player, Position
from tests.helpers import FixedCardSource, card

DOT = card((0, 0))
COLUMN = card((-1, 0), (0, 0), (1, 0))  # vertical bar of 3


def make_game(cards=(DOT,), **config):
    return Game(GameConfig(**config), FixedCardSource(*cards))


def test_players_alternate_and_card_changes():
    game = make_game(cards=(DOT, COLUMN))
    assert game.current_player is Player.RED and game.current_card == DOT
    game.play(Position(0, 0))
    assert game.current_player is Player.BLUE and game.current_card == COLUMN


def test_card_is_clipped_at_the_edges_and_changes_are_reported():
    game = make_game(cards=(card((-1, -1), (0, 0)),))
    result = game.play(Position(0, 0))
    assert result.changed_cells == (Position(0, 0),)
    assert game.scores()[Player.RED] == 1


def test_colors_can_be_overwritten():
    game = make_game()
    game.play(Position(1, 1))
    result = game.play(Position(1, 1))
    assert result.changed_cells == (Position(1, 1),)
    assert game.grid[1][1] is Player.BLUE
    assert game.scores() == {Player.RED: 0, Player.BLUE: 1}


def test_completing_a_line_gives_a_bonus_turn():
    game = make_game(cards=(COLUMN,), board_size=3, total_turns=10)
    result = game.play(Position(1, 1))
    assert result.new_lines == ("column 2",)
    assert result.bonus_turn
    assert game.current_player is Player.RED


def test_an_already_full_line_does_not_give_another_bonus():
    game = make_game(cards=(COLUMN,), board_size=3, total_turns=10)
    game.play(Position(1, 1))
    result = game.play(Position(1, 1))  # bonus move, same line, nothing new
    assert result.new_lines == () and not result.bonus_turn
    assert game.current_player is Player.BLUE


def test_turns_are_shared_and_bonus_moves_consume_them():
    game = make_game(total_turns=4)
    for _ in range(4):
        game.play(Position(0, 0))
    assert game.is_over and game.turns_played == 4
    with pytest.raises(InvalidMoveError):
        game.play(Position(0, 0))


def test_no_bonus_on_the_last_turn():
    game = make_game(cards=(COLUMN,), board_size=3, total_turns=1)
    result = game.play(Position(1, 1))
    assert result.new_lines and not result.bonus_turn
    assert game.is_over


def test_winner_and_draw():
    game = make_game(total_turns=1)
    game.play(Position(0, 0))
    assert game.winner() is Player.RED

    game = make_game(total_turns=2)
    game.play(Position(0, 0))
    game.play(Position(4, 4))
    assert game.winner() is None


def test_outside_the_board_is_rejected():
    game = make_game()
    with pytest.raises(InvalidMoveError):
        game.play(Position(5, 0))
    assert game.turns_played == 0


def test_invalid_config_is_rejected():
    with pytest.raises(ValueError):
        GameConfig(card_size=4)
    with pytest.raises(ValueError):
        GameConfig(colored_cells=10)
