import pytest

from core import Board, Player, Position


def test_paint_count_and_overwrite():
    board = Board(3)
    board.paint([Position(0, 0), Position(1, 1)], Player.RED)
    board.paint([Position(1, 1)], Player.BLUE)
    assert board.count(Player.RED) == 1
    assert board.count(Player.BLUE) == 1
    assert board.get(Position(1, 1)) is Player.BLUE


def test_out_of_board_is_rejected_even_for_negative_indexes():
    board = Board(3)
    with pytest.raises(ValueError):
        board.paint([Position(-1, 0)], Player.RED)
    with pytest.raises(ValueError):
        board.get(Position(0, 3))


def test_rows_columns_and_diagonals():
    board = Board(3)
    board.paint([Position(0, c) for c in range(3)], Player.RED)
    board.paint([Position(r, 2) for r in range(3)], Player.RED)
    assert board.completed_lines(Player.RED) == {"row 1", "column 3"}
    board.paint([Position(i, i) for i in range(3)], Player.BLUE)
    assert board.completed_lines(Player.BLUE) == {"diagonal \\"}
    assert board.completed_lines(Player.RED) == set()  # row 1 / column 3 broken


def test_diagonals_can_be_disabled():
    board = Board(3, diagonals_count=False)
    board.paint([Position(i, i) for i in range(3)], Player.RED)
    assert board.completed_lines(Player.RED) == frozenset()


def test_snapshot_is_a_copy():
    board = Board(2)
    snap = board.snapshot()
    board.paint([Position(0, 0)], Player.RED)
    assert snap[0][0] is None


def test_players_are_compared_by_value_not_identity():
    """Two Player objects with the same name and color are the same player."""
    copy = Player("RED", Player.RED.color)
    assert copy is not Player.RED and copy == Player.RED
    board = Board(2)
    board.paint([Position(0, 0), Position(0, 1)], Player.RED)
    assert board.count(copy) == 2
    assert board.completed_lines(copy) == {"row 1"}
    board.fill(copy)
    assert board.is_filled_with(Player.RED)
    board.clear_player(copy)
    assert board.count(Player.RED) == 0
