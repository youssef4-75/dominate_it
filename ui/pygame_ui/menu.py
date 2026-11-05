"""pygame implementation of Menu."""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, TypeVar

import pygame

from ui.base import AfterMatchChoice, MainChoice, Menu
from ui.pygame_ui.drawing import Button, draw_text
from ui.pygame_ui.layout import Layout
from ui.pygame_ui.theme import BACKGROUND, MUTED, TEXT, WINDOW_SIZE
from ui.pygame_ui.window import PygameWindow

T = TypeVar("T")
WIDTH = WINDOW_SIZE[0]


def main_menu_buttons() -> List[Button]:
    size = (240, 60)
    return [
        Button("Play", pygame.Rect((WIDTH - size[0]) // 2, 340, *size), MainChoice.PLAY),
        Button("Quit", pygame.Rect((WIDTH - size[0]) // 2, 420, *size), MainChoice.QUIT),
    ]


def after_match_buttons() -> List[Button]:
    """Shown in the sidebar, next to the game-over board."""
    size = (230, 56)
    x = Layout.SIDEBAR_X
    return [
        Button("Replay", pygame.Rect(x, 250, *size), AfterMatchChoice.REPLAY),
        Button("Home", pygame.Rect(x, 322, *size), AfterMatchChoice.HOME),
    ]


class PygameMenu(Menu):
    def __init__(self, window: PygameWindow) -> None:
        self._window = window

    def ask_main_choice(self) -> MainChoice:
        def draw_background() -> None:
            screen, fonts = self._window.screen, self._window.fonts
            screen.fill(BACKGROUND)
            draw_text(screen, fonts.title, "GRID COLOR WAR", (WIDTH // 2, 220), TEXT, "center")
            draw_text(screen, fonts.small, "Stamp cards, paint the grid, win the most cells.",
                      (WIDTH // 2, 262), MUTED, "center")

        keys = {
            pygame.K_RETURN: MainChoice.PLAY, pygame.K_1: MainChoice.PLAY,
            pygame.K_ESCAPE: MainChoice.QUIT, pygame.K_2: MainChoice.QUIT,
        }
        return self._wait(main_menu_buttons(), keys, MainChoice.QUIT, draw_background)

    def ask_after_match(self) -> AfterMatchChoice:
        final_screen = self._window.screen.copy()  # the game-over scene
        keys = {
            pygame.K_r: AfterMatchChoice.REPLAY,
            pygame.K_h: AfterMatchChoice.HOME, pygame.K_ESCAPE: AfterMatchChoice.HOME,
        }
        return self._wait(
            after_match_buttons(), keys, AfterMatchChoice.HOME,
            lambda: self._window.screen.blit(final_screen, (0, 0)),
        )

    def show_goodbye(self) -> None:
        self._window.close()

    # -- internals ---------------------------------------------------------
    def _wait(
        self,
        buttons: List[Button],
        keys: Dict[int, T],
        if_closed: T,
        draw_background: Callable[[], object],
    ) -> T:
        w = self._window
        while True:
            events = w.pump()
            if w.closed:
                return if_closed
            for event in events:
                if event.type == pygame.KEYDOWN and event.key in keys:
                    return keys[event.key]
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for button in buttons:
                        if button.rect.collidepoint(event.pos):
                            return button.value  # type: ignore[return-value]
            draw_background()
            mouse = pygame.mouse.get_pos()
            for button in buttons:
                button.draw(w.screen, w.fonts, button.rect.collidepoint(mouse))
            w.flip()
