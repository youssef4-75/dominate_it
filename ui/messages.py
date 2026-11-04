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
    name = fmt(result.player)
    text = (
        f"{name} played at row {result.position.row + 1}, "
        f"col {result.position.col + 1} "
        f"({len(result.changed_cells)} cell(s) changed)."
    )
    if result.new_lines:
        text += f"\n  Full line completed: {', '.join(result.new_lines)}!"
    if result.bonus_turn:
        text += f"\n  {name} plays again!"
    return text


def describe_outcome(game: Game, fmt: NameFormatter = plain_name) -> str:
    winner = game.winner()
    if winner is None:
        return "It's a draw!"
    return f"{fmt(winner)} wins!"
