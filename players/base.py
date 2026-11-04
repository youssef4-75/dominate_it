"""Interface: how a participant decides its move."""
from __future__ import annotations

from abc import ABC, abstractmethod

from core import Game, Position


class MatchAborted(Exception):
    """Raised by a selector when its participant wants to abandon the match."""


class MoveSelector(ABC):
    """Receives the whole game as context and returns a decision.

    Implementations can be a console human, a socket client, a neural
    network, an LLM... The game gives them everything they need:
    `game.current_player`, `game.grid`, `game.current_card`,
    `game.turns_left`, `game.painted_cells(position)`, ...
    Selectors must treat the game as READ-ONLY: only the match runner
    calls `game.play()`.
    """

    @abstractmethod
    def choose_move(self, game: Game) -> Position:
        """Return the board position where the current card's center goes.

        Raise MatchAborted to abandon the match.
        """
