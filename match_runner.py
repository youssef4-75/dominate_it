"""Glue: plays ONE match by connecting a Game, a Renderer and move selectors."""
from __future__ import annotations

from enum import Enum
from typing import Callable, Mapping

from core import Game, Player
from players import MatchAborted, MoveSelector
from ui import Renderer

GameFactory = Callable[[], Game]


class MatchStatus(Enum):
    FINISHED = "finished"
    ABORTED = "aborted"


class MatchRunner:
    def __init__(
        self,
        game_factory: GameFactory,
        renderer: Renderer,
        selectors: Mapping[Player, MoveSelector],
    ) -> None:
        missing = [p.name for p in Player if p not in selectors]
        if missing:
            raise ValueError(f"No move selector for: {', '.join(missing)}")
        self._game_factory = game_factory
        self._renderer = renderer
        self._selectors = selectors

    def run(self) -> MatchStatus:
        game = self._game_factory()
        last_move = None
        while not game.is_over:
            self._renderer.render_game(game, last_move)
            selector = self._selectors[game.current_player]
            try:
                position = selector.choose_move(game)
            except MatchAborted:
                return MatchStatus.ABORTED
            last_move = game.play(position)

        self._renderer.render_game(game, last_move)
        self._renderer.render_game_over(game)
        return MatchStatus.FINISHED
