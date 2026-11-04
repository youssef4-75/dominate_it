"""The game rules. Pure logic: no printing, no input, no randomness of its own."""
from __future__ import annotations

from typing import Dict, Optional, Tuple

from core.board import Board
from core.card import Card, CardSource
from core.config import GameConfig
from core.errors import InvalidMoveError
from core.models import Grid, MoveResult, Player, Position


class Game:
    def __init__(self, config: GameConfig, card_source: CardSource) -> None:
        self._config = config
        self._card_source = card_source
        self._board = Board(config.board_size, config.diagonals_count)
        self._current_player = config.first_player
        self._turns_played = 0
        self._card = card_source.next_card()

    # -- read-only state (this is the "context" given to move selectors) ---
    @property
    def config(self) -> GameConfig:
        return self._config

    @property
    def size(self) -> int:
        return self._board.size

    @property
    def grid(self) -> Grid:
        return self._board.snapshot()

    @property
    def current_player(self) -> Player:
        return self._current_player

    @property
    def current_card(self) -> Card:
        return self._card

    @property
    def turns_played(self) -> int:
        return self._turns_played

    @property
    def turns_left(self) -> int:
        return self._config.total_turns - self._turns_played

    @property
    def is_over(self) -> bool:
        return self.turns_left <= 0

    def scores(self) -> Dict[Player, int]:
        return {player: self._board.count(player) for player in Player}

    def winner(self) -> Optional[Player]:
        """The player with the most cells, or None for a draw."""
        scores = self.scores()
        if scores[Player.RED] == scores[Player.BLUE]:
            return None
        return max(scores, key=scores.get)

    def painted_cells(self, position: Position) -> Tuple[Position, ...]:
        """Board cells the current card would paint if centered on `position`."""
        return tuple(
            p for p in self._current_card_cells(position) if self._board.contains(p)
        )

    # -- the only way to change the game -----------------------------------
    def play(self, position: Position) -> MoveResult:
        if self.is_over:
            raise InvalidMoveError("The game is over.")
        if not self._board.contains(position):
            raise InvalidMoveError(f"{tuple(position)} is outside the board.")

        player = self._current_player
        lines_before = self._board.completed_lines(player)

        painted = self.painted_cells(position)
        changed = tuple(p for p in painted if self._board.get(p) is not player)
        self._board.paint(painted, player)

        new_lines = tuple(sorted(self._board.completed_lines(player) - lines_before))
        self._turns_played += 1
        bonus = bool(new_lines) and not self.is_over

        self._advance(bonus)
        return MoveResult(player, Position(*position), changed, new_lines, bonus)

    # -- internals ---------------------------------------------------------
    def _current_card_cells(self, position: Position) -> Tuple[Position, ...]:
        return self._card.cells_at(Position(*position))

    def _advance(self, bonus: bool) -> None:
        if self.is_over:
            return
        if not bonus:
            self._current_player = self._current_player.other
        self._card = self._card_source.next_card()
