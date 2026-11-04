"""Console implementation of Renderer."""
from __future__ import annotations

from typing import Callable, Optional

from core import Game, MoveResult, Player, Position
from ui.base import Renderer
from ui.cmd.ansi import BOLD, RESET, cell_block, clear_screen, paint_name
from ui.messages import describe_move, describe_outcome, describe_start

TITLE = f"{BOLD}=== GRID COLOR WAR ==={RESET}"


class CmdRenderer(Renderer):
    def __init__(
        self,
        print_fn: Callable[[str], None] = print,
        clear_fn: Callable[[], None] = clear_screen,
    ) -> None:
        self._print = print_fn
        self._clear = clear_fn

    def render_game(self, game: Game, last_move: Optional[MoveResult]) -> None:
        out = self._print
        scores = game.scores()
        self._clear()
        out(f"{TITLE}\n")
        for player in Player:
            out(f"  {paint_name(player, 4)}: {scores[player]:>2} cells")
        out(f"  Turns left: {game.turns_left} / {game.config.total_turns}\n")
        out(self._board_text(game))
        out("")
        message = (
            describe_start(game, paint_name)
            if last_move is None
            else describe_move(last_move, paint_name)
        )
        out(message + "\n")
        if not game.is_over:
            out(
                f"  {paint_name(game.current_player)}'s card "
                f"(◆ = center, placed on the cell you choose):\n"
            )
            out(self._card_text(game))
            out("")

    def render_game_over(self, game: Game) -> None:
        scores = game.scores()
        self._print(f"{BOLD}=== GAME OVER ==={RESET}")
        self._print(
            f"  {paint_name(Player.RED)}: {scores[Player.RED]}   "
            f"{paint_name(Player.BLUE)}: {scores[Player.BLUE]}"
        )
        self._print(f"\n  {BOLD}{describe_outcome(game, paint_name)}{RESET}\n")

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _board_text(game: Game) -> str:
        lines = ["     " + " ".join(f" {c + 1}" for c in range(game.size))]
        for r, row in enumerate(game.grid):
            blocks = " ".join(cell_block(cell) for cell in row)
            lines.append(f"  {r + 1}  {blocks}")
        return "\n".join(lines)

    @staticmethod
    def _card_text(game: Game) -> str:
        card = game.current_card
        player = game.current_player
        lines = []
        for dr in range(-card.radius, card.radius + 1):
            blocks = []
            for dc in range(-card.radius, card.radius + 1):
                colored = Position(dr, dc) in card.offsets
                blocks.append(
                    cell_block(player if colored else None, marker=(dr == 0 and dc == 0))
                )
            lines.append("      " + " ".join(blocks))
        return "\n".join(lines)
