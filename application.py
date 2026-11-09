"""Glue: the home page / settings / replay loop around matches."""
from __future__ import annotations

from typing import Optional

from core import GameConfig
from match_runner import MatchRunner, MatchStatus
from ui import AfterMatchChoice, MainChoice, Menu


class Application:
    """home -> (Play) -> settings of THIS game -> match -> Replay (same settings) / Home."""

    def __init__(self, menu: Menu, match_runner: MatchRunner, config: Optional[GameConfig] = None) -> None:
        self._menu = menu
        self._match_runner = match_runner
        self._config = config or GameConfig()  # settings proposed for the next game

    def run(self) -> None:
        while self._menu.ask_main_choice() is MainChoice.PLAY:
            config = self._menu.ask_game_config(self._config)
            if config is None:  # the player went back to the home page
                continue
            self._config = config  # the next game starts from these settings
            self._play_until_home(config)
        self._menu.show_goodbye()

    def _play_until_home(self, config: GameConfig) -> None:
        while True:
            status = self._match_runner.run(config)
            if status is MatchStatus.ABORTED:
                return
            if self._menu.ask_after_match() is not AfterMatchChoice.REPLAY:
                return
