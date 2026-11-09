import random

from core import GameConfig, Position, RandomCardSource
from tests.helpers import card


def test_cells_at_is_relative_to_center():
    c = card((-1, -1), (0, 0), (1, 0))
    assert c.cells_at(Position(2, 2)) == (Position(1, 1), Position(2, 2), Position(3, 2))


def test_random_source_respects_config():
    config = GameConfig()
    source = RandomCardSource.from_config(config, random.Random(0))
    for _ in range(50):
        c = source.next_card()
        assert len(c.offsets) == config.colored_cells
        assert all(abs(o.row) <= c.radius and abs(o.col) <= c.radius for o in c.offsets)


def test_random_source_is_reproducible_with_a_seed():
    a = RandomCardSource(rng=random.Random(42)).next_card()
    b = RandomCardSource(rng=random.Random(42)).next_card()
    assert a == b


# ---------------------------------------------------------------- pattern helpers
from core import Card  # noqa: E402


def test_a_3x3_card_has_8_lines_and_9_positions():
    c = card((0, 0))
    assert len(c.lines()) == 8 and len(c.positions()) == 9
    assert all(len(line) == 3 for line in c.lines())


def test_has_line():
    assert card((-1, -1), (0, 0), (1, 1), (0, 1)).has_line()  # a diagonal
    assert not card((-1, 0), (0, 1), (1, -1), (1, 1)).has_line()


def test_with_line_keeps_the_number_of_cells_and_forms_a_line():
    base = card((-1, 0), (0, 1), (1, -1), (1, 1))
    boosted = base.with_line()
    assert boosted.has_line() and len(boosted.offsets) == 4
    assert Position(1, -1) in boosted.offsets  # it reused the line that fitted the card best
    assert base.offsets == frozenset(Position(*o) for o in [(-1, 0), (0, 1), (1, -1), (1, 1)])  # not mutated


def test_with_line_leaves_a_card_that_already_has_a_line_unchanged():
    base = card((-1, -1), (0, 0), (1, 1), (0, 1))
    assert base.with_line().offsets == base.offsets


def test_with_line_cannot_help_a_card_with_fewer_cells_than_a_line():
    base = card((0, 0), (1, 1))
    assert base.with_line().offsets == base.offsets


def test_with_neutral_center_moves_the_center_cell_to_the_nearest_free_cell():
    base = card((0, 0), (-1, -1), (1, 1), (0, 1))
    neutral = base.with_neutral_center()
    assert Position(0, 0) not in neutral.offsets and len(neutral.offsets) == 4
    assert Position(-1, 0) in neutral.offsets  # nearest free cell (ties: first in reading order)


def test_with_neutral_center_leaves_a_card_with_a_neutral_center_unchanged():
    base = card((-1, -1), (1, 1), (0, 1), (1, 0))
    assert base.with_neutral_center().offsets == base.offsets


def test_notes_are_ignored_when_comparing_cards():
    base = card((0, 0))
    assert base.with_note("hello") == base and base.with_note("hello").note == "hello"
