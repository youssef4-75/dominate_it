"""Rule `line_streak_wipe`: too many line-completing moves in a row wipe your cells."""
from __future__ import annotations

from core.rules.base import MoveContext, Option, Rule


class LineStreakWipe(Rule):
    name = "line_streak_wipe"
    description = (
        "Completing a line on `limit` consecutive moves makes the player lose all its cells "
        "(they become neutral); the next player plays."
    )
    options_spec = {"limit": Option(3, "Lines in a row", minimum=1, maximum=20)}

    def after_move(self, ctx: MoveContext) -> None:
        if ctx.line_streak >= self.option("limit"):
            ctx.board.clear_player(ctx.player)
            ctx.add_event("cells_wiped", "Too many lines in a row: {player} loses all cells!")
            ctx.pass_turn()
