"""Rule `full_board_flip`: filling the whole grid gives it to the opponent (off by default)."""
from __future__ import annotations

from core.rules.base import MoveContext, Rule


class FullBoardFlip(Rule):
    name = "full_board_flip"
    description = (
        "A player who colors the whole grid with its color sees every cell switch to the "
        "next player's color, and the next player plays. (Alternative to full_board_win.)"
    )
    enabled_by_default = False

    def after_move(self, ctx: MoveContext) -> None:
        # `changed`: a move that changes nothing on an already-full board must not flip it back.
        if ctx.changed and ctx.board.is_filled_with(ctx.player):
            ctx.board.fill(ctx.next_player)
            ctx.add_event(
                "board_flipped",
                "The whole board is {player}! Every cell switches to {next}, and {next} plays.",
            )
            ctx.pass_turn()
