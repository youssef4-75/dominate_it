from typing import Set, Tuple

from core import Game


class ScreenInterface:
  def render_board(self, game: Game) -> str:
    """Render the board."""
    ...

  def render_card(self, game: Game) -> str:
    """Render the card."""
    ...

  def is_created_line(self, game: Game, card: Set[Tuple[int, int]]) -> str:
    """Check if a line is created by the last move."""
    ...

