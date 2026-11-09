"""The card (colored pattern to stamp) and where cards come from."""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, FrozenSet, Optional, Tuple

from core.models import Position

if TYPE_CHECKING:  # avoids an import cycle: config -> rules -> card
    from core.config import GameConfig


@dataclass(frozen=True)
class Card:
    """A square pattern. `offsets` are the colored cells, relative to the center.

    `note` is an optional text a rule can attach ("Catch-up boost...").
    It is ignored when comparing cards.
    """

    size: int
    offsets: frozenset  # frozenset[Position], each (d_row, d_col) in -radius..radius
    note: str = field(default="", compare=False)

    @property
    def radius(self) -> int:
        return self.size // 2

    def cells_at(self, center: Position) -> Tuple[Position, ...]:
        """Board positions covered by the colored cells (NOT clipped to the board)."""
        return tuple(
            Position(center.row + o.row, center.col + o.col)
            for o in sorted(self.offsets)
        )

    # -- pattern helpers (pure: they return a new Card) ---------------------
    def positions(self) -> Tuple[Position, ...]:
        """Every cell of the card, colored or not (row by row)."""
        span = range(-self.radius, self.radius + 1)
        return tuple(Position(dr, dc) for dr in span for dc in span)

    def lines(self) -> Tuple[FrozenSet[Position], ...]:
        """All rows, columns and both diagonals of the card."""
        span = range(-self.radius, self.radius + 1)
        rows = [frozenset(Position(r, c) for c in span) for r in span]
        cols = [frozenset(Position(r, c) for r in span) for c in span]
        diagonals = [
            frozenset(Position(i, i) for i in span),
            frozenset(Position(i, -i) for i in span),
        ]
        return tuple(rows + cols + diagonals)

    def has_line(self) -> bool:
        return any(line <= self.offsets for line in self.lines())

    def with_line(self) -> "Card":
        """Same number of colored cells, but they now form a full line + extra cells.

        Picks the line that already shares the most cells with this card, keeps
        as many of the card's other cells as are needed. Unchanged if the card has
        fewer colored cells than a line is long.
        """
        count = len(self.offsets)
        if count < self.size:
            return self
        best = max(self.lines(), key=lambda line: len(line & self.offsets))
        extra = sorted(self.offsets - best)[: count - self.size]
        return replace(self, offsets=frozenset(best) | frozenset(extra))

    def with_neutral_center(self) -> "Card":
        """Same number of colored cells, but the center cell is not colored.

        A colored center moves to the nearest free cell. Unchanged if the center
        is already neutral.
        """
        center = Position(0, 0)
        free = [p for p in self.positions() if p not in self.offsets]
        if center not in self.offsets or not free:
            return self
        nearest = min(free, key=lambda p: (abs(p.row) + abs(p.col), p))
        return replace(self, offsets=(self.offsets - {center}) | {nearest})

    def with_note(self, note: str) -> "Card":
        return replace(self, note=note)


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
