"""Colors, window size and fonts."""
from __future__ import annotations

from dataclasses import dataclass

import pygame

from core import Player

WINDOW_SIZE = (560, 760)

BACKGROUND = (24, 26, 33)
PANEL = (36, 39, 49)
EMPTY_CELL = (58, 62, 74)
TEXT = (235, 237, 242)
MUTED = (150, 155, 168)
WHITE = (255, 255, 255)
BUTTON = (52, 57, 72)
BUTTON_HOVER = (74, 82, 104)

PLAYER_COLORS = {
    Player.RED: (226, 72, 72),
    Player.BLUE: (66, 133, 230),
}


@dataclass(frozen=True)
class Fonts:
    title: pygame.font.Font
    big: pygame.font.Font
    normal: pygame.font.Font
    small: pygame.font.Font

    @classmethod
    def create(cls) -> "Fonts":
        """Needs pygame to be initialised."""
        return cls(
            title=pygame.font.Font(None, 44),
            big=pygame.font.Font(None, 38),
            normal=pygame.font.Font(None, 30),
            small=pygame.font.Font(None, 23),
        )
