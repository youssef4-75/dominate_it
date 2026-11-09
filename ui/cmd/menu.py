"""Console implementation of Menu."""
from __future__ import annotations

from typing import Callable, Optional

from core import GameConfig
from ui.base import AfterMatchChoice, MainChoice, Menu
from ui.cmd.ansi import BOLD, RESET, clear_screen


class CmdMenu(Menu):
    def __init__(
        self,
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[[str], None] = print,
        clear_fn: Callable[[], None] = clear_screen,
    ) -> None:
        self._input = input_fn
        self._print = print_fn
        self._clear = clear_fn

    def ask_main_choice(self) -> MainChoice:
        while True:
            self._clear()
            self._print(f"{BOLD}=== GRID COLOR WAR ==={RESET}\n")
            self._print("  1) Play")
            self._print("  2) Quit\n")
            choice = self._input("Choice: ").strip()
            if choice == "1":
                return MainChoice.PLAY
            if choice == "2":
                return MainChoice.QUIT

    def ask_game_config(self, current: GameConfig) -> Optional[GameConfig]:
        """No settings screen in the console: use the command-line options (--players, --disable...)."""
        return current

    def ask_after_match(self) -> AfterMatchChoice:
        answer = self._input("Replay (r) or go back to home page (h)? ").strip().lower()
        return AfterMatchChoice.REPLAY if answer == "r" else AfterMatchChoice.HOME

    def show_goodbye(self) -> None:
        self._print("Bye!")
