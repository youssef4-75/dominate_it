"""Plain data types shared by the whole project (no logic, no I/O)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple, Optional, Tuple


class Player(Enum):
    RED = "R"
    BLUE = "B"

    @property
    def other(self) -> "Player":
        return Player.BLUE if self is Player.RED else Player.RED


class Position(NamedTuple):
    """A (row, col) coordinate, 0-indexed."""

    row: int
    col: int


Cell = Optional[Player]  # None means empty
Grid = Tuple[Tuple[Cell, ...], ...]  # immutable snapshot of the board


@dataclass(frozen=True)
class MoveResult:
    """What happened when a card was played."""

    player: Player
    position: Position
    changed_cells: Tuple[Position, ...]
    new_lines: Tuple[str, ...]  # human readable, e.g. "row 2", "column 4"
    bonus_turn: bool
    board_flipped: bool = False  # the player filled the whole board: it went to the opponent
    cells_wiped: bool = False  # too many lines in a row: the player lost all its cells
    line_streak: int = 0  # consecutive line-completing moves of the player, after this move
