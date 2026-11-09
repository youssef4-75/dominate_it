"""The game engine. Pure logic: no printing, no input, no randomness of its own.

The engine only knows the basic mechanics:
* a card is stamped on the board, centered on the chosen cell (overwriting colors);
* 2 to 6 players play in turn (the order of `config.players`); the turns are shared by all;
* when the turns run out, the player with the most cells wins.

EVERYTHING ELSE (bonus turn, penalties, early win, better/worse cards...) is a
RULE (see core/rules/): independent objects that the engine calls in order, that
you can switch on/off with `GameConfig.rules`, and that you can test alone.
"""
from __future__ import annotations

from collections import deque
import random
from typing import Deque, Dict, Optional, Sequence, Tuple

from core.board import Board
from core.card import Card, CardSource, RandomCardSource
from core.config import GameConfig
from core.errors import InvalidMoveError
from core.models import Grid, MoveResult, Player, Position
from core.rules.base import CardContext, MoveContext, Rule
from core.rules.line_streak_wipe import LineStreakWipe


class Game:
    def __init__(
        self,
        config: GameConfig,
        card_source: CardSource,
        rules: Optional[Sequence[Rule]] = None,
    ) -> None:
        """`rules` replaces the rules built from `config.rules` (useful in tests)."""
        self._config = config
        self._card_source = card_source
        self._rules = list(rules) if rules is not None else config.rules.build()
        self._board = Board(config.board_size, config.diagonals_count)
        self._players = config.players
        self._turn = 0  # index in self._players of the player who plays now
        self._turns_played = 0
        self._line_streak = 0
        self._ended = False  # a rule ended the game early
        self._forced_winner: Optional[Player] = None
        first = card_source.next_card()
        # Cards shown in advance. They are "base" cards: rules may adjust a card
        # at the moment it becomes the current one (the player is known by then).
        self._upcoming: Deque[Card] = deque(
            card_source.next_card() for _ in range(config.preview_cards)
        )
        self._card = self._adapt_card(first)

    # -- read-only state (this is the "context" given to move selectors) ---
    @property
    def config(self) -> GameConfig:
        return self._config

    @property
    def rule_names(self) -> Tuple[str, ...]:
        """Names of the rules in force, in execution order."""
        return tuple(rule.name for rule in self._rules)

    @property
    def players(self) -> Tuple[Player, ...]:
        """Everybody, in turn order."""
        return self._players

    @property
    def size(self) -> int:
        return self._board.size

    @property
    def grid(self) -> Grid:
        return self._board.snapshot()

    @property
    def current_player(self) -> Player:
        return self._players[self._turn]

    @property
    def next_player(self) -> Player:
        """Who plays after the current player (turn order), bonus turns apart."""
        return self._players[(self._turn + 1) % len(self._players)]

    @property
    def current_card(self) -> Card:
        """The card to play now (already adjusted by the rules, see `Card.note`)."""
        return self._card

    @property
    def upcoming_cards(self) -> Tuple[Card, ...]:
        """The cards that will come after the current one, in order.

        Only cards that will really be played. They are shown as drawn: a rule
        (catch_up_cards) may still adjust them when they become current.
        """
        if self.is_over:
            return ()
        visible = max(0, min(len(self._upcoming), self.turns_left - 1))
        return tuple(list(self._upcoming)[:visible])

    @property
    def line_streak(self) -> int:
        """Consecutive moves of the current player that each completed a line."""
        return self._line_streak

    @property
    def line_streak_limit(self) -> Optional[int]:
        """The limit of the `line_streak_wipe` rule, or None if that rule is off."""
        for rule in self._rules:
            if isinstance(rule, LineStreakWipe):
                return rule.option("limit")
        return None

    @property
    def turns_played(self) -> int:
        return self._turns_played

    @property
    def turns_left(self) -> int:
        return self._config.total_turns - self._turns_played

    @property
    def is_over(self) -> bool:
        return self._ended or self.turns_left <= 0

    def scores(self) -> Dict[Player, int]:
        return {player: self._board.count(player) for player in self._players}

    def winners(self) -> Tuple[Player, ...]:
        """Everybody who tops the ranking: one player, or several in case of a tie.

        A rule can end the game with a given winner (e.g. full_board_win with
        `winner=mover`); otherwise it is the player(s) with the most cells.
        """
        if self._forced_winner is not None:
            return (self._forced_winner,)
        scores = self.scores()
        best = max(scores.values())
        return tuple(player for player in self._players if scores[player] == best)

    def winner(self) -> Optional[Player]:
        """The single winner, or None when several players are tied."""
        winners = self.winners()
        return winners[0] if len(winners) == 1 else None

    def painted_cells(self, position: Position) -> Tuple[Position, ...]:
        """Board cells the current card would paint if centered on `position`."""
        cells = self._card.cells_at(Position(*position))
        return tuple(p for p in cells if self._board.contains(p))

    # -- the only way to change the game -----------------------------------
    def play(self, position: Position) -> MoveResult:
        if self.is_over:
            raise InvalidMoveError("The game is over.")
        if not self._board.contains(position):
            raise InvalidMoveError(f"{tuple(position)} is outside the board.")

        # 1. basic mechanics: stamp the card
        player = self.current_player
        lines_before = self._board.completed_lines(player)
        painted = self.painted_cells(position)
        changed = tuple(p for p in painted if self._board.get(p) != player)
        self._board.paint(painted, player)

        new_lines = tuple(sorted(self._board.completed_lines(player) - lines_before))
        self._turns_played += 1
        self._line_streak = self._line_streak + 1 if new_lines else 0

        # 2. the rules, in order, until one of them decides the move
        ctx = MoveContext(
            board=self._board, player=player, next_player=self.next_player,
            players=self._players, changed=changed, new_lines=new_lines,
            line_streak=self._line_streak, turns_left=self.turns_left,
        )
        for rule in self._rules:
            rule.after_move(ctx)
            if ctx.decided:
                break

        if ctx.game_ended:
            self._ended = True
            self._forced_winner = ctx.winner
        keeps_turn = ctx.bonus_turn and not self.is_over

        if self.is_over:
            next_player = None
        else:
            next_player = player if keeps_turn else self.next_player
        result = MoveResult(
            player, Position(*position), changed, new_lines, keeps_turn, next_player,
            tuple(ctx.events), self._line_streak if keeps_turn else 0,
        )
        self._advance(keeps_turn)
        return result

    # -- internals ---------------------------------------------------------
    def _advance(self, keeps_turn: bool) -> None:
        if self.is_over:
            return
        if not keeps_turn:
            self._turn = (self._turn + 1) % len(self._players)
            self._line_streak = 0
        self._card = self._adapt_card(self._draw_base_card())

    def _draw_base_card(self) -> Card:
        if not self._upcoming:  # preview_cards == 0
            return self._card_source.next_card()
        card = self._upcoming.popleft()
        self._upcoming.append(self._card_source.next_card())
        return card

    def _adapt_card(self, card: Card) -> Card:
        """Let the rules adjust a card, now that we know who plays it and the scores."""
        ctx = CardContext(self.current_player, self.scores(), self._players)
        for rule in self._rules:
            card = rule.adjust_card(card, ctx)
        return card


def new_game(config: GameConfig, rng: Optional[random.Random] = None) -> Game:
    """A fresh game with random cards. The usual way to start a game from a config."""
    return Game(config, RandomCardSource.from_config(config, rng))
