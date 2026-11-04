"""Composition root: the ONLY place that picks concrete implementations.

To change the interface or the kind of players, change the lines marked
[SWAP] and nothing else.
"""
from __future__ import annotations

from typing import Optional

from application import Application
from core import Game, GameConfig, Player, RandomCardSource
from match_runner import MatchRunner
from ui.cmd import CmdHumanPlayer, CmdMenu, CmdRenderer, enable_ansi


def build_application(config: Optional[GameConfig] = None) -> Application:
    config = config or GameConfig()

    def new_game() -> Game:
        return Game(config, RandomCardSource.from_config(config))

    renderer = CmdRenderer()  # [SWAP] pyplot / tkinter / pygame renderer
    menu = CmdMenu()  # [SWAP] matching menu
    human = CmdHumanPlayer()  # [SWAP] socket / neural network / LLM selector
    selectors = {Player.RED: human, Player.BLUE: human}

    match_runner = MatchRunner(new_game, renderer, selectors)
    return Application(menu, match_runner)


def main() -> None:
    enable_ansi()
    build_application().run()


if __name__ == "__main__":
    main()
