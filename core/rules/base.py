"""The interface every rule implements, and the contexts rules work with.

A rule is a small, independent object with two optional hooks:

* `after_move(ctx)`   called after a card was stamped on the board. It can
                      change the board, grant a bonus turn, pass the turn,
                      end the game, and report what it did as events.
* `adjust_card(card, ctx)`  called when a card becomes the current card (known
                      player, known scores). It can return a modified card.

Rules run in a fixed order (see `core/rules/registry.py`). As soon as a rule
*decides* the move (`ctx.pass_turn()` or `ctx.end_game()`), the remaining
`after_move` hooks are skipped.

A rule is tested alone: build a `MoveContext` / `CardContext` by hand and call
its hook, no `Game` needed (see tests/test_rule_units.py).
"""
from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Mapping, Optional, Tuple

from core.models import Player, Position, RuleEvent

if TYPE_CHECKING:
    from core.board import Board
    from core.card import Card


@dataclass(frozen=True)
class Option:
    """A tunable setting of a rule: its default and what values are allowed.

    The settings screens (pygame, web) are built from these, so a new option
    appears there without touching any UI code.
    """

    default: Any
    label: str = ""
    minimum: Optional[int] = None  # for integer options
    maximum: Optional[int] = None
    choices: Optional[Tuple[str, ...]] = None  # for text options

    @property
    def kind(self) -> str:
        return "choice" if self.choices else "int"

    def check(self, rule: str, key: str, value: Any) -> Any:
        """Return the value if valid, else raise ValueError."""
        if self.choices is not None:
            if value not in self.choices:
                raise ValueError(f"Rule '{rule}': option '{key}' must be one of {list(self.choices)}")
            return value
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"Rule '{rule}': option '{key}' must be a whole number")
        if self.minimum is not None and value < self.minimum:
            raise ValueError(f"Rule '{rule}': option '{key}' must be >= {self.minimum}")
        if self.maximum is not None and value > self.maximum:
            raise ValueError(f"Rule '{rule}': option '{key}' must be <= {self.maximum}")
        return value


@dataclass
class MoveContext:
    """The move that was just played. Rules read the facts and write the effects."""

    # facts (set by the Game, rules may change the board)
    board: "Board"
    player: Player
    next_player: Player  # who plays after this move (turn order), unless a bonus turn is granted
    players: Tuple[Player, ...]  # everybody, in turn order
    changed: Tuple[Position, ...]  # cells whose color changed because of this move
    new_lines: Tuple[str, ...]  # full lines of `player` that did not exist before this move
    line_streak: int  # consecutive line-completing moves of `player`, this one included
    turns_left: int  # shared turns left after this move
    # effects (written by rules)
    events: List[RuleEvent] = field(default_factory=list)
    bonus_turn: bool = False
    decided: bool = False  # True: remaining rules are skipped
    game_ended: bool = False
    winner: Optional[Player] = None

    def add_event(self, code: str, text: str) -> None:
        self.events.append(RuleEvent(code, text))

    def pass_turn(self) -> None:
        """The player's turn ends now: no bonus, the opponent plays, later rules skipped."""
        self.bonus_turn = False
        self.decided = True

    def end_game(self, winner: Optional[Player] = None) -> None:
        """The game ends right now, later rules skipped.

        `winner` given: that player wins. Omitted: the player with the most cells wins
        (a tie is a draw).
        """
        self.bonus_turn = False
        self.decided = True
        self.game_ended = True
        self.winner = winner


@dataclass
class CardContext:
    """The situation in which a card is about to be played."""

    player: Player  # who will play the card
    scores: Mapping[Player, int]  # cells owned by each player right now (everybody is a key)
    players: Tuple[Player, ...]  # everybody, in turn order


class Rule(ABC):
    """Base class of all rules. Override the hooks you need."""

    name: ClassVar[str]  # unique id, used on the command line and in RuleSet
    description: ClassVar[str]  # one sentence, shown by --list-rules
    enabled_by_default: ClassVar[bool] = True
    options_spec: ClassVar[Mapping[str, Option]] = {}  # tunable settings

    @classmethod
    def option_defaults(cls) -> Dict[str, Any]:
        return {key: spec.default for key, spec in cls.options_spec.items()}

    def __init__(self, **options: Any) -> None:
        unknown = set(options) - set(self.options_spec)
        if unknown:
            raise ValueError(
                f"Rule '{self.name}' has no option(s) {sorted(unknown)}; "
                f"valid: {sorted(self.options_spec)}"
            )
        self.options = {
            key: self.options_spec[key].check(self.name, key, value)
            for key, value in {**self.option_defaults(), **options}.items()
        }

    def option(self, key: str) -> Any:
        return self.options[key]

    def after_move(self, ctx: MoveContext) -> None:
        """Called after the card was stamped. Default: does nothing."""

    def adjust_card(self, card: "Card", ctx: CardContext) -> "Card":
        """Called when `card` becomes the current card. Default: unchanged."""
        return card
