"""A human playing with the mouse: implements MoveSelector."""
from __future__ import annotations

import pygame

from core import Game, Position
from players import MatchAborted, MoveSelector
from ui.pygame_ui.drawing import draw_preview
from ui.pygame_ui.layout import Layout
from ui.pygame_ui.window import PygameWindow


class PygameHumanPlayer(MoveSelector):
    """Click a cell to stamp the card there. Esc or closing the window aborts.

    One instance can serve both players: it reads `game.current_player`.
    """

    def __init__(self, window: PygameWindow) -> None:
        self._window = window

    def choose_move(self, game: Game) -> Position:
        w = self._window
        layout = Layout(game.size)
        scene = w.screen.copy()  # what the renderer just drew
        while True:
            events = w.pump()
            if w.closed:
                raise MatchAborted()
            for event in events:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    raise MatchAborted()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    position = layout.cell_at(event.pos)
                    if position is not None:
                        return position
            w.screen.blit(scene, (0, 0))
            draw_preview(w.screen, layout, game, layout.cell_at(pygame.mouse.get_pos()))
            w.flip()
