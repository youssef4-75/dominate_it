"""The pygame window, shared by the renderer, the menu and the human player."""
from __future__ import annotations

from typing import List, Tuple

import pygame

from ui.pygame_ui.theme import WINDOW_SIZE, Fonts


class PygameWindow:
    """Owns the display, the clock and the event queue.

    `closed` becomes True when the user closes the window; the components that
    wait for the user (menu, human player) then bail out, so the application
    ends cleanly. `close()` releases pygame.
    """

    def __init__(
        self,
        size: Tuple[int, int] = WINDOW_SIZE,
        title: str = "Grid Color War",
        fps: int = 60,
    ) -> None:
        pygame.display.init()  # no pygame.init(): the game needs no audio
        pygame.font.init()
        self.screen = pygame.display.set_mode(size)
        pygame.display.set_caption(title)
        self.fonts = Fonts.create()
        self._clock = pygame.time.Clock()
        self._fps = fps
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def pump(self) -> List[pygame.event.Event]:
        """Fetch pending events; flags the window as closed on QUIT."""
        if not pygame.display.get_init():
            self._closed = True
            return []
        events = pygame.event.get()
        if any(event.type == pygame.QUIT for event in events):
            self._closed = True
        return events

    def flip(self) -> None:
        """Show the frame, keep the OS happy, cap the frame rate."""
        pygame.display.flip()
        pygame.event.pump()  # keeps the window responsive; does not drop events
        self._clock.tick(self._fps)

    def close(self) -> None:
        if pygame.display.get_init():
            pygame.quit()
        self._closed = True
