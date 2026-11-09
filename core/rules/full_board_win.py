"""Rule `full_board_win`: when the grid is completely covered, the game ends at once."""
from __future__ import annotations

from core.rules.base import MoveContext, Option, Rule


class FullBoardWin(Rule):
    name = "full_board_win"
    description = (
        "As soon as no cell is neutral any more (covered by one player or by several), the game "
        "ends immediately. `winner`: most_cells = the player with the most cells wins; "
        "mover = the player whose card filled the last cell wins."
    )
    options_spec = {
        "winner": Option("most_cells", "Winner is", choices=("most_cells", "mover")),
    }

    def after_move(self, ctx: MoveContext) -> None:
        if not ctx.board.is_full():
            return
        if ctx.board.is_filled_with(ctx.player):  # one single player owns everything
            ctx.add_event("board_filled_win", "{player} filled the whole grid and wins immediately!")
            ctx.end_game(ctx.player)
        elif self.option("winner") == "mover":
            ctx.add_event("board_filled_win", "The grid is full: {player} filled the last cell and wins!")
            ctx.end_game(ctx.player)
        else:
            ctx.add_event("board_filled_win", "The grid is full: the game ends now!")
            ctx.end_game()  # the player with the most cells wins
