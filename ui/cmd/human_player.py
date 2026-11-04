"""A human playing through the console: implements MoveSelector."""
from __future__ import annotations

from typing import Callable, Optional

from core import Game, Position
from players import MatchAborted, MoveSelector
from ui.cmd.ansi import DIM, RESET, paint_name

QUIT_WORDS = ("q", "quit", "exit")


def parse_position(raw: str, size: int) -> Optional[Position]:
    """'3 4' or '3,4' (1-indexed) -> Position(2, 3), or None if invalid."""
    parts = raw.replace(",", " ").split()
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        return None
    row, col = int(parts[0]) - 1, int(parts[1]) - 1
    if 0 <= row < size and 0 <= col < size:
        return Position(row, col)
    return None


class CmdHumanPlayer(MoveSelector):
    """One instance can serve both players: it reads `game.current_player`."""

    def __init__(
        self,
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[[str], None] = print,
    ) -> None:
        self._input = input_fn
        self._print = print_fn

    def choose_move(self, game: Game) -> Position:
        prompt = (
            f"{paint_name(game.current_player)} - choose a cell "
            f"as 'row col' (1-{game.size}), or 'q' to quit: "
        )
        while True:
            raw = self._input(prompt).strip().lower()
            if raw in QUIT_WORDS:
                raise MatchAborted()
            position = parse_position(raw, game.size)
            if position is not None:
                return position
            self._print(f"  {DIM}Invalid input. Example: 3 4  (row 3, column 4){RESET}")
