"""Rule `line_bonus`: completing a NEW full line gives another move."""
from __future__ import annotations

from core.rules.base import MoveContext, Rule


class LineBonus(Rule):
    name = "line_bonus"
    description = "Completing a new full line (row, column, diagonal) gives the player another move."

    def after_move(self, ctx: MoveContext) -> None:
        # No bonus on the very last turn: there is nothing left to play.
        if ctx.new_lines and ctx.turns_left > 0:
            ctx.bonus_turn = True
            lines = ", ".join(ctx.new_lines)
            ctx.add_event("line_bonus", f"Full line completed: {lines}!\n{{player}} plays again!")
