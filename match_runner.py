"""Glue: plays ONE match by connecting a Game, a Renderer and move selectors."""
from __future__ import annotations

from enum import Enum
from typing import Callable, Mapping, Optional, Union

from core import Game, GameConfig, Player
from players import MatchAborted, MoveSelector
from ui import Renderer

GameFactory = Callable[[GameConfig], Game]


class MatchStatus(Enum):
    FINISHED = "finished"
    ABORTED = "aborted"


class MatchRunner:
    """`selectors`: ONE MoveSelector used by every player (hot-seat), or a mapping
    {Player: MoveSelector} (e.g. a human for RED, a bot for BLUE)."""

    def __init__(
        self,
        game_factory: GameFactory,
        renderer: Renderer,
        selectors: Union[MoveSelector, Mapping[Player, MoveSelector]],
    ) -> None:
        self._game_factory = game_factory
        self._renderer = renderer
        self._selectors = selectors

    def _selector_for(self, player: Player) -> Optional[MoveSelector]:
        if isinstance(self._selectors, MoveSelector):
            return self._selectors
        return self._selectors.get(player)

    def run(self, config: GameConfig) -> MatchStatus:
        game = self._game_factory(config)
        missing = [p.name for p in game.players if self._selector_for(p) is None]
        if missing:
            raise ValueError(f"No move selector for: {', '.join(missing)}")

        last_move = None
        while not game.is_over:
            self._renderer.render_game(game, last_move)
            selector = self._selector_for(game.current_player)
            try:
                position = selector.choose_move(game)
            except MatchAborted:
                return MatchStatus.ABORTED
            last_move = game.play(position)

        self._renderer.render_game(game, last_move)
        self._renderer.render_game_over(game)
        return MatchStatus.FINISHED
