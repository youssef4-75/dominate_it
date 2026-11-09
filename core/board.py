"""The grid and its geometry (cells, painting, full lines)."""
from __future__ import annotations

from typing import Iterable, Iterator, List, Tuple

from core.models import Cell, Grid, Player, Position


class Board:
    def __init__(self, size: int, diagonals_count: bool = True) -> None:
        self._size = size
        self._diagonals_count = diagonals_count
        self._cells: List[List[Cell]] = [[None] * size for _ in range(size)]

    @property
    def size(self) -> int:
        return self._size

    def contains(self, position: Position) -> bool:
        row, col = position
        return 0 <= row < self._size and 0 <= col < self._size

    def get(self, position: Position) -> Cell:
        self._check(position)
        return self._cells[position[0]][position[1]]

    def paint(self, positions: Iterable[Position], player: Player) -> None:
        """Overwrite the given cells with the player's color."""
        for position in positions:
            self._check(position)
            self._cells[position[0]][position[1]] = player

    def is_full(self) -> bool:
        """True when no cell is neutral any more (whoever owns them)."""
        return all(cell is not None for row in self._cells for cell in row)

    def is_filled_with(self, player: Player) -> bool:
        return all(cell == player for row in self._cells for cell in row)

    def fill(self, player: Player) -> None:
        """Give every cell to `player`."""
        self._cells = [[player] * self._size for _ in range(self._size)]

    def clear_player(self, player: Player) -> None:
        """Make every cell owned by `player` neutral again."""
        self._cells = [[None if cell == player else cell for cell in row] for row in self._cells]

    def count(self, player: Player) -> int:
        return sum(row.count(player) for row in self._cells)

    def completed_lines(self, player: Player) -> frozenset:
        """Labels of every line fully filled with the player's color."""
        return frozenset(
            label
            for label, positions in self._lines()
            if all(self.get(p) == player for p in positions)
        )

    def snapshot(self) -> Grid:
        """Immutable copy of the current state."""
        return tuple(tuple(row) for row in self._cells)

    # -- internals ---------------------------------------------------------
    def _check(self, position: Position) -> None:
        # Explicit check: negative indexes would silently wrap around in Python.
        if not self.contains(position):
            raise ValueError(f"{tuple(position)} is outside the board")

    def _lines(self) -> Iterator[Tuple[str, List[Position]]]:
        n = self._size
        for r in range(n):
            yield f"row {r + 1}", [Position(r, c) for c in range(n)]
        for c in range(n):
            yield f"column {c + 1}", [Position(r, c) for r in range(n)]
        if self._diagonals_count:
            yield "diagonal \\", [Position(i, i) for i in range(n)]
            yield "diagonal /", [Position(i, n - 1 - i) for i in range(n)]
