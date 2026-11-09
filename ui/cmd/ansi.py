"""Terminal helpers: ANSI colors (24-bit, from each player's RGB) and screen clearing."""
from __future__ import annotations

import os
from typing import Tuple

from core import Cell, Player

RESET = "\033[0m"
BOLD = "\033[1m"
WHITE = "\033[97m"
DIM = "\033[90m"

_BG_EMPTY = "\033[100m"
_BG_NEUTRAL = "\033[47m"  # light gray: cards whose owner is not known yet
_BLACK = "\033[30m"


def _fg(color: Tuple[int, int, int]) -> str:
    return "\033[38;2;{};{};{}m".format(*color)


def _bg(color: Tuple[int, int, int]) -> str:
    return "\033[48;2;{};{};{}m".format(*color)


def enable_ansi() -> None:
    if os.name == "nt":
        os.system("")  # enables ANSI escape codes in Windows terminals


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def paint_name(player: Player, width: int = 0) -> str:
    """Player name in bold, in the player's color."""
    return f"{BOLD}{_fg(player.color)}{player.name:<{width}}{RESET}"


def cell_block(cell: Cell, marker: bool = False) -> str:
    """Two-characters-wide colored block."""
    background = _bg(cell.color) if cell is not None else _BG_EMPTY
    return f"{background}{WHITE}{'◆ ' if marker else '  '}{RESET}"


def neutral_block(colored: bool, marker: bool = False) -> str:
    """Block of an upcoming card: light gray if colored (owner unknown yet)."""
    if colored:
        return f"{_BG_NEUTRAL}{_BLACK}{'◆ ' if marker else '  '}{RESET}"
    return f"{_BG_EMPTY}{WHITE}{'◆ ' if marker else '  '}{RESET}"
