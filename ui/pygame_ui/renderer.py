"""pygame implementation of Renderer."""
from __future__ import annotations

from typing import Optional

from core import Game, MoveResult
from ui.base import Renderer
from ui.pygame_ui.drawing import draw_game_over, draw_scene
from ui.pygame_ui.layout import Layout
from ui.pygame_ui.window import PygameWindow


class PygameRenderer(Renderer):
    def __init__(self, window: PygameWindow) -> None:
        self._window = window

    def render_game(self, game: Game, last_move: Optional[MoveResult]) -> None:
        w = self._window
        draw_scene(w.screen, w.fonts, Layout(game.size), game, last_move)
        w.flip()

    def render_game_over(self, game: Game) -> None:
        w = self._window
        draw_game_over(w.screen, w.fonts, Layout(game.size), game)
        w.flip()
