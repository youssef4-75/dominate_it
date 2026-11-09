"""UI-independent texts, reusable by every renderer.

`fmt` lets a renderer decorate player names (colors, bold...) without
duplicating the wording.
"""
from __future__ import annotations

from typing import Callable

from core import Game, MoveResult, Player

NameFormatter = Callable[[Player], str]


def plain_name(player: Player) -> str:
    return player.name


def describe_start(game: Game, fmt: NameFormatter = plain_name) -> str:
    return f"Game start! {fmt(game.current_player)} begins."


def describe_move(result: MoveResult, fmt: NameFormatter = plain_name) -> str:
    """The move, then what each rule did (the rules own their wording: RuleEvent.text)."""
    name = fmt(result.player)
    following = fmt(result.next_player) if result.next_player is not None else ""
    text = (
        f"{name} played at row {result.position.row + 1}, "
        f"col {result.position.col + 1} "
        f"({len(result.changed_cells)} cell(s) changed)."
    )
    for event in result.events:
        for line in event.text.format(player=name, next=following).splitlines():
            text += f"\n  {line}"
    return text


def describe_rules(game: Game) -> str:
    """One line listing the rules in force."""
    return "Rules: " + (", ".join(game.rule_names) if game.rule_names else "none (plain game)")


def describe_outcome(game: Game, fmt: NameFormatter = plain_name) -> str:
    winners = game.winners()
    if len(winners) == 1:
        return f"{fmt(winners[0])} wins!"
    if len(winners) == len(game.players):
        return "It's a draw!"
    return " and ".join(fmt(w) for w in winners) + " tie for the win!"
