"""Composition root: the ONLY place that picks concrete implementations.

    python main.py                # pygame window (default)
    python main.py --ui cmd       # console

To plug in another interface or another kind of player (bot, socket, LLM...),
change `_build_ui` / the `selectors` mapping and nothing else.
"""
from __future__ import annotations

import argparse
from typing import Optional, Sequence, Tuple

from application import Application
from core import Game, GameConfig, Player, RandomCardSource
from match_runner import MatchRunner
from players import MoveSelector
from ui import Menu, Renderer

DEFAULT_UI = "pygame"
UI_CHOICES = ("pygame", "cmd")


def _build_ui(ui: str) -> Tuple[Renderer, Menu, MoveSelector]:
    """Returns (renderer, menu, human move selector) for the chosen interface."""
    if ui == "pygame":
        # Imported lazily so console users don't need pygame installed.
        try:
            from ui.pygame_ui import (
                PygameHumanPlayer, PygameMenu, PygameRenderer, PygameWindow,
            )
        except ImportError as error:
            raise SystemExit(
                "The pygame interface needs pygame:  pip install pygame\n"
                "(or play in the console:  python main.py --ui cmd)"
            ) from error

        window = PygameWindow()
        return PygameRenderer(window), PygameMenu(window), PygameHumanPlayer(window)

    from ui.cmd import CmdHumanPlayer, CmdMenu, CmdRenderer, enable_ansi

    enable_ansi()
    return CmdRenderer(), CmdMenu(), CmdHumanPlayer()


def build_application(config: Optional[GameConfig] = None, ui: str = DEFAULT_UI) -> Application:
    config = config or GameConfig()

    def new_game() -> Game:
        return Game(config, RandomCardSource.from_config(config))

    renderer, menu, human = _build_ui(ui)
    selectors = {Player.RED: human, Player.BLUE: human}  # [SWAP] bots, sockets, LLMs...
    return Application(menu, MatchRunner(new_game, renderer, selectors))


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Grid Color War")
    parser.add_argument("--ui", choices=UI_CHOICES, default=DEFAULT_UI)
    args = parser.parse_args(argv)
    build_application(ui=args.ui).run()  # pass config=GameConfig(...) to change the rules


if __name__ == "__main__":
    main()
