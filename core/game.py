"""The game rules. Pure logic: no printing, no input, no randomness of its own.

Rules implemented here (see `play`):
* the current card is stamped on the board, centered on the chosen cell;
* completing a NEW full line gives the player another move (bonus turn);
* PENALTY 1 - filling the whole board with your color gives every cell to the
  opponent, and the opponent plays (no bonus);
* PENALTY 2 - completing lines on `line_streak_limit` consecutive moves wipes all
  your cells (they become neutral), and the opponent plays (no bonus);
  if both happen on the same move, penalty 1 wins;
* the turns are shared by both players; the player with most cells wins.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, Dict, Optional, Tuple

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
        self._line_streak = 0
        # current card + the upcoming ones, drawn in advance so they can be shown
        self._cards: Deque[Card] = deque(
            card_source.next_card() for _ in range(1 + config.preview_cards)
        )

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
        return self._cards[0]

    @property
    def upcoming_cards(self) -> Tuple[Card, ...]:
        """The cards that will come after the current one, in order.

        Only cards that will really be played: near the end of the match there
        are fewer than `config.preview_cards`. Their color is not known yet
        (a bonus turn or a penalty changes who plays next).
        """
        visible = max(0, min(len(self._cards) - 1, self.turns_left - 1))
        return tuple(list(self._cards)[1 : 1 + visible])

    @property
    def line_streak(self) -> int:
        """Consecutive moves of the current player that each completed a line."""
        return self._line_streak

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
        cells = self.current_card.cells_at(Position(*position))
        return tuple(p for p in cells if self._board.contains(p))

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
        self._line_streak = self._line_streak + 1 if new_lines else 0

        board_flipped = cells_wiped = False
        limit = self._config.line_streak_limit
        # `changed` matters: a move that changes nothing on a board that is already
        # entirely yours (after a flip) must not flip it back.
        if self._config.full_board_flip and changed and self._board.is_filled_with(player):
            self._board.fill(player.other)
            board_flipped = True
        elif limit is not None and self._line_streak >= limit:
            self._board.clear_player(player)
            cells_wiped = True

        penalized = board_flipped or cells_wiped
        if penalized:
            self._line_streak = 0
        bonus = bool(new_lines) and not penalized and not self.is_over

        result = MoveResult(
            player, Position(*position), changed, new_lines, bonus,
            board_flipped, cells_wiped, self._line_streak,
        )
        self._advance(bonus)
        return result

    # -- internals ---------------------------------------------------------
    def _advance(self, bonus: bool) -> None:
        if self.is_over:
            return
        if not bonus:
            self._current_player = self._current_player.other
            self._line_streak = 0
        self._cards.popleft()
        self._cards.append(self._card_source.next_card())
