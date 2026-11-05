"""Geometry: where things are on the screen, and which cell a pixel belongs to."""
from __future__ import annotations

from typing import Optional, Tuple

import pygame

from core import Position
from ui.pygame_ui.theme import WINDOW_SIZE


class Layout:
    GAP = 4
    BOARD_TOP = 124
    BOARD_AREA = 440  # max width/height of the board
    CARD_CELL = 34
    CARD_GAP = 3
    CARD_ORIGIN = (30, 604)

    def __init__(self, board_size: int, window_width: int = WINDOW_SIZE[0]) -> None:
        self.board_size = board_size
        self.cell = (self.BOARD_AREA - self.GAP * (board_size + 1)) // board_size
        side = board_size * self.cell + self.GAP * (board_size + 1)
        self.board_rect = pygame.Rect((window_width - side) // 2, self.BOARD_TOP, side, side)

    def cell_rect(self, position: Position) -> pygame.Rect:
        pitch = self.cell + self.GAP
        return pygame.Rect(
            self.board_rect.x + self.GAP + position.col * pitch,
            self.board_rect.y + self.GAP + position.row * pitch,
            self.cell,
            self.cell,
        )

    def cell_at(self, pixel: Tuple[int, int]) -> Optional[Position]:
        """Board cell under a pixel (gaps belong to the nearest cell), or None."""
        for row in range(self.board_size):
            for col in range(self.board_size):
                position = Position(row, col)
                if self.cell_rect(position).inflate(self.GAP, self.GAP).collidepoint(pixel):
                    return position
        return None

    def card_cell_rect(self, row_index: int, col_index: int) -> pygame.Rect:
        pitch = self.CARD_CELL + self.CARD_GAP
        x, y = self.CARD_ORIGIN
        return pygame.Rect(
            x + col_index * pitch, y + row_index * pitch, self.CARD_CELL, self.CARD_CELL
        )
