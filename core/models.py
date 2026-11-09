"""Plain data types shared by the whole project (no logic, no I/O)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, NamedTuple, Optional, Tuple


@dataclass(frozen=True)
class Player:
    """A player: a name and a color. Players are compared by value and are hashable.

    The turn order of a game is the order of `GameConfig.players`.
    """

    name: str
    color: Tuple[int, int, int]  # RGB 0-255

    RED: ClassVar["Player"]
    BLUE: ClassVar["Player"]
    GREEN: ClassVar["Player"]
    YELLOW: ClassVar["Player"]
    PURPLE: ClassVar["Player"]
    ORANGE: ClassVar["Player"]

    @property
    def hex_color(self) -> str:
        r, g, b = self.color
        return f"#{r:02x}{g:02x}{b:02x}"

    def __str__(self) -> str:
        return self.name


Player.RED = Player("RED", (226, 72, 72))
Player.BLUE = Player("BLUE", (66, 133, 230))
Player.GREEN = Player("GREEN", (72, 180, 100))
Player.YELLOW = Player("YELLOW", (230, 196, 60))
Player.PURPLE = Player("PURPLE", (160, 100, 220))
Player.ORANGE = Player("ORANGE", (240, 140, 50))

# Colors available, in the order they are given to players 1, 2, 3...
PALETTE: Tuple[Player, ...] = (
    Player.RED, Player.BLUE, Player.GREEN, Player.YELLOW, Player.PURPLE, Player.ORANGE,
)
MIN_PLAYERS = 2
MAX_PLAYERS = len(PALETTE)


def players_for(count: int) -> Tuple[Player, ...]:
    """The first `count` players of the palette (RED, BLUE, GREEN...)."""
    if not MIN_PLAYERS <= count <= MAX_PLAYERS:
        raise ValueError(f"The number of players must be between {MIN_PLAYERS} and {MAX_PLAYERS}")
    return PALETTE[:count]


class Position(NamedTuple):
    """A (row, col) coordinate, 0-indexed."""

    row: int
    col: int


Cell = Optional[Player]  # None means empty
Grid = Tuple[Tuple[Cell, ...], ...]  # immutable snapshot of the board


@dataclass(frozen=True)
class RuleEvent:
    """Something a rule did during a move, with its own wording.

    `text` may contain the placeholders {player} (the mover) and {next} (the player
    who plays after this move); each UI fills them in (console adds colors).
    `code` is a stable id.
    """

    code: str
    text: str


@dataclass(frozen=True)
class MoveResult:
    """What happened when a card was played."""

    player: Player
    position: Position
    changed_cells: Tuple[Position, ...]
    new_lines: Tuple[str, ...]  # human readable, e.g. "row 2", "column 4"
    bonus_turn: bool  # the same player plays again
    next_player: Optional[Player] = None  # who plays next (None: the game is over)
    events: Tuple[RuleEvent, ...] = ()  # what the rules did, in order
    line_streak: int = 0  # consecutive line-completing moves of the player, after this move

    def has_event(self, code: str) -> bool:
        return any(event.code == code for event in self.events)
