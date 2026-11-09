"""Console implementation of Renderer."""
from __future__ import annotations

from typing import Callable, List, Optional

from core import Card, Game, MoveResult, Player, Position
from ui.base import Renderer
from ui.cmd.ansi import BOLD, DIM, RESET, cell_block, clear_screen, neutral_block, paint_name
from ui.messages import describe_move, describe_outcome, describe_rules, describe_start

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
        width = max(len(p.name) for p in game.players)
        for player in game.players:
            out(f"  {paint_name(player, width)}: {scores[player]:>2} cells")
        out(f"  Turns left: {game.turns_left} / {game.config.total_turns}")
        limit = game.line_streak_limit
        if limit is not None:
            out(f"  Line streak: {game.line_streak} / {limit}")
        out("")
        out(self._board_text(game))
        out("")
        message = (
            describe_start(game, paint_name)
            if last_move is None
            else describe_move(last_move, paint_name)
        )
        out(message + "\n")
        if not game.is_over:
            out("  ◆ = center of the card, placed on the cell you choose\n")
            out(self._cards_text(game))
            if game.current_card.note:
                out(f"\n  {BOLD}{game.current_card.note}{RESET}")
            out("")
        out(f"  {DIM}{describe_rules(game)}{RESET}")

    def render_game_over(self, game: Game) -> None:
        scores = game.scores()
        self._print(f"{BOLD}=== GAME OVER ==={RESET}")
        self._print("  " + "   ".join(f"{paint_name(p)}: {scores[p]}" for p in game.players))
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
    def _card_rows(card: Card, player: Optional[Player]) -> List[str]:
        """Text rows of one card. `player` None = neutral (upcoming card)."""
        rows = []
        for dr in range(-card.radius, card.radius + 1):
            blocks = []
            for dc in range(-card.radius, card.radius + 1):
                colored = Position(dr, dc) in card.offsets
                center = dr == 0 and dc == 0
                if player is None:
                    blocks.append(neutral_block(colored, center))
                else:
                    blocks.append(cell_block(player if colored else None, center))
            rows.append(" ".join(blocks))
        return rows

    @classmethod
    def _cards_text(cls, game: Game) -> str:
        """The current card, followed by the upcoming ones (Next, Then...)."""
        player = game.current_player
        card_width, pitch, first_col = 8, 12, 24  # visible width / spacing of 3x3 cards
        labels = ["Next", "Then"] + [f"+{i}" for i in range(3, 20)]

        title = f"  {player.name}'s card"
        header = f"  {paint_name(player)}'s card" + " " * (first_col - len(title))
        header += "".join(labels[i].ljust(pitch) for i in range(len(game.upcoming_cards)))

        current = cls._card_rows(game.current_card, player)
        upcoming = [cls._card_rows(card, None) for card in game.upcoming_cards]
        lines = [header]
        for row in range(len(current)):
            line = "      " + current[row] + " " * (first_col - 6 - card_width)
            line += (" " * (pitch - card_width)).join(rows[row] for rows in upcoming)
            lines.append(line)
        return "\n".join(lines)
