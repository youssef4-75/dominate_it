"""Game settings, in one immutable object. Each game has its own."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Dict, Mapping, Optional, Tuple

from core.models import MAX_PLAYERS, MIN_PLAYERS, PALETTE, Player, players_for
from core.rules.ruleset import RuleSet


@dataclass(frozen=True)
class GameConfig:
    board_size: int = 5
    card_size: int = 3  # must be odd so the card has a center
    colored_cells: int = 4  # colored cells on each card
    total_turns: int = 30  # shared by ALL players (bonus moves count)
    diagonals_count: bool = True  # do diagonals count as "full lines"?
    preview_cards: int = 0  # how many upcoming cards are visible (besides the current one)
    players: Tuple[Player, ...] = PALETTE[:2]  # in turn order: the first one plays first
    # Which special rules are ON (and their options). See core/rules/.
    rules: RuleSet = field(default_factory=RuleSet.default)

    def __post_init__(self) -> None:
        if self.board_size < 1:
            raise ValueError("board_size must be >= 1")
        if self.card_size < 1 or self.card_size % 2 == 0:
            raise ValueError("card_size must be a positive odd number")
        if not 1 <= self.colored_cells <= self.card_size ** 2:
            raise ValueError("colored_cells must fit inside the card")
        if self.total_turns < 1:
            raise ValueError("total_turns must be >= 1")
        if self.preview_cards < 0:
            raise ValueError("preview_cards must be >= 0")
        object.__setattr__(self, "players", tuple(self.players))
        if not MIN_PLAYERS <= len(self.players) <= MAX_PLAYERS:
            raise ValueError(f"players: between {MIN_PLAYERS} and {MAX_PLAYERS} are needed")
        if len({p.name for p in self.players}) != len(self.players):
            raise ValueError("players must have different names")
        if not isinstance(self.rules, RuleSet):
            raise ValueError("rules must be a RuleSet (e.g. RuleSet.default())")

    # -- (de)serialization: JSON-friendly, used by the web API and the settings screens ---
    def to_dict(self) -> Dict[str, Any]:
        return {
            "num_players": len(self.players),
            "board_size": self.board_size,
            "card_size": self.card_size,
            "colored_cells": self.colored_cells,
            "total_turns": self.total_turns,
            "diagonals_count": self.diagonals_count,
            "preview_cards": self.preview_cards,
            "rules": self.rules.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], base: Optional["GameConfig"] = None) -> "GameConfig":
        """Settings from a dict. Missing keys keep the value of `base` (default config).

        `num_players` picks the first N colors of the palette. Raises ValueError with a
        readable message on unknown keys, wrong types or out-of-range values.
        """
        base = base or cls()
        if not isinstance(data, Mapping):
            raise ValueError("The configuration must be an object")
        unknown = set(data) - set(_FIELD_KINDS) - {"num_players", "rules"}
        if unknown:
            raise ValueError(f"Unknown setting(s): {sorted(unknown)}")
        values: Dict[str, Any] = {}
        for key, kind in _FIELD_KINDS.items():
            if key in data:
                value = data[key]
                if kind == "bool" and not isinstance(value, bool):
                    raise ValueError(f"{key} must be true or false")
                if kind == "int" and (isinstance(value, bool) or not isinstance(value, int)):
                    raise ValueError(f"{key} must be a whole number")
                values[key] = value
        if "num_players" in data:
            count = data["num_players"]
            if isinstance(count, bool) or not isinstance(count, int):
                raise ValueError("num_players must be a whole number")
            values["players"] = players_for(count)
        if "rules" in data:
            values["rules"] = RuleSet.from_dict(data["rules"])
        return replace(base, **values)


_FIELD_KINDS = {
    "board_size": "int", "card_size": "int", "colored_cells": "int", "total_turns": "int",
    "diagonals_count": "bool", "preview_cards": "int",
}


@dataclass(frozen=True)
class Setting:
    """A game parameter shown in the settings screens (the rules are described by RuleSet)."""

    key: str
    label: str
    kind: str  # "int" | "bool"
    minimum: int = 0
    maximum: int = 0
    step: int = 1


# What the settings screens (pygame, web) let the player change, in display order.
SETTINGS: Tuple[Setting, ...] = (
    Setting("num_players", "Players", "int", MIN_PLAYERS, MAX_PLAYERS),
    Setting("board_size", "Board size", "int", 3, 9),
    Setting("total_turns", "Turns (shared by all)", "int", 5, 500, step=5),
    Setting("colored_cells", "Colored cells per card", "int", 1, 9),
    Setting("preview_cards", "Cards shown ahead", "int", 0, 3),
    Setting("diagonals_count", "Diagonals count as lines", "bool"),
)
