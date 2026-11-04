"""Glue: the home page / replay loop around matches."""
from __future__ import annotations

from match_runner import MatchRunner, MatchStatus
from ui import AfterMatchChoice, MainChoice, Menu


class Application:
    def __init__(self, menu: Menu, match_runner: MatchRunner) -> None:
        self._menu = menu
        self._match_runner = match_runner

    def run(self) -> None:
        while self._menu.ask_main_choice() is MainChoice.PLAY:
            self._play_until_home()
        self._menu.show_goodbye()

    def _play_until_home(self) -> None:
        while True:
            status = self._match_runner.run()
            if status is MatchStatus.ABORTED:
                return
            if self._menu.ask_after_match() is not AfterMatchChoice.REPLAY:
                return
