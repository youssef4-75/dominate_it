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
