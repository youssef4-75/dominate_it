"""Game settings, in one immutable object."""
from __future__ import annotations

from dataclasses import dataclass

from core.models import Player
from core.vars import BOARD_SIZE, TURNS_PER_PLAYER, CARD_SIZE, CARD_COLORED_CELLS

@dataclass(frozen=True)
class GameConfig:
    board_size: int = BOARD_SIZE
    card_size: int = CARD_SIZE  # must be odd so the card has a center
    colored_cells: int = CARD_COLORED_CELLS  # colored cells on each card
    total_turns: int = TURNS_PER_PLAYER # shared by both players (bonus moves count)
    diagonals_count: bool = True  # do diagonals count as "full lines"?
    first_player: Player = Player.RED

    def __post_init__(self) -> None:
        if self.board_size < 1:
            raise ValueError("board_size must be >= 1")
        if self.card_size < 1 or self.card_size % 2 == 0:
            raise ValueError("card_size must be a positive odd number")
        if not 1 <= self.colored_cells <= self.card_size ** 2:
            raise ValueError("colored_cells must fit inside the card")
        if self.total_turns < 1:
            raise ValueError("total_turns must be >= 1")
