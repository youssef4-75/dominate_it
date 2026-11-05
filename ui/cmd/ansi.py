"""Terminal helpers: ANSI colors and screen clearing."""
from __future__ import annotations

import os

from core import Cell, Player

RESET = "\033[0m"
BOLD = "\033[1m"
WHITE = "\033[97m"
DIM = "\033[90m"

_FG = {Player.RED: "\033[91m", Player.BLUE: "\033[94m"}
_BG = {Player.RED: "\033[41m", Player.BLUE: "\033[44m"}
_BG_EMPTY = "\033[100m"
_BG_NEUTRAL = "\033[47m"  # light gray: cards whose owner is not known yet
_BLACK = "\033[30m"


def enable_ansi() -> None:
    if os.name == "nt":
        os.system("")  # enables ANSI escape codes in Windows terminals


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def paint_name(player: Player, width: int = 0) -> str:
    """Player name in bold, in the player's color."""
    return f"{BOLD}{_FG[player]}{player.name:<{width}}{RESET}"


def cell_block(cell: Cell, marker: bool = False) -> str:
    """Two-characters-wide colored block."""
    background = _BG[cell] if cell is not None else _BG_EMPTY
    return f"{background}{WHITE}{'◆ ' if marker else '  '}{RESET}"


def neutral_block(colored: bool, marker: bool = False) -> str:
    """Block of an upcoming card: light gray if colored (owner unknown yet)."""
    if colored:
        return f"{_BG_NEUTRAL}{_BLACK}{'◆ ' if marker else '  '}{RESET}"
    return f"{_BG_EMPTY}{WHITE}{'◆ ' if marker else '  '}{RESET}"
