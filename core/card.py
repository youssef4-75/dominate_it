"""The card (colored pattern to stamp) and where cards come from."""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple

from core.config import GameConfig
from core.models import Position


@dataclass(frozen=True)
class Card:
    """A square pattern. `offsets` are the colored cells, relative to the center."""

    size: int
    offsets: frozenset  # frozenset[Position], each (d_row, d_col) in -radius..radius

    @property
    def radius(self) -> int:
        return self.size // 2

    def cells_at(self, center: Position) -> Tuple[Position, ...]:
        """Board positions covered by the colored cells (NOT clipped to the board)."""
        return tuple(
            Position(center.row + o.row, center.col + o.col)
            for o in sorted(self.offsets)
        )


class CardSource(ABC):
    """Interface: whatever decides which card comes next."""

    @abstractmethod
    def next_card(self) -> Card: ...


class RandomCardSource(CardSource):
    def __init__(
        self,
        size: int = 3,
        colored_cells: int = 4,
        rng: Optional[random.Random] = None,
    ) -> None:
        self._size = size
        self._colored_cells = colored_cells
        self._rng = rng or random.Random()
        radius = size // 2
        self._all_offsets = [
            Position(dr, dc)
            for dr in range(-radius, radius + 1)
            for dc in range(-radius, radius + 1)
        ]

    @classmethod
    def from_config(
        cls, config: GameConfig, rng: Optional[random.Random] = None
    ) -> "RandomCardSource":
        return cls(config.card_size, config.colored_cells, rng)

    def next_card(self) -> Card:
        chosen = self._rng.sample(self._all_offsets, self._colored_cells)
        return Card(self._size, frozenset(chosen))
