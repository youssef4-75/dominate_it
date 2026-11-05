"""Geometry: where things are on the screen, and which cell a pixel belongs to.

Window (landscape):  board on the left, sidebar (cards, streak, buttons) on the right.
"""
from __future__ import annotations

from typing import Optional, Tuple

import pygame

from core import Position


class Layout:
    # board
    GAP = 4
    BOARD_LEFT = 30
    BOARD_TOP = 124
    BOARD_AREA = 440  # max width/height of the board
    # sidebar
    SIDEBAR_X = 510
    CARD_ORIGIN = (SIDEBAR_X, 156)  # current card (top-left)
    CARD_CELL = 40
    CARD_GAP = 4
    NEXT_ORIGIN = (SIDEBAR_X, 336)  # upcoming cards (top-left of the first one)
    NEXT_CELL = 26
    NEXT_GAP = 3
    NEXT_SPACING = 26  # space between two upcoming cards
    STREAK_POS = (SIDEBAR_X, 452)

    def __init__(self, board_size: int) -> None:
        self.board_size = board_size
        self.cell = (self.BOARD_AREA - self.GAP * (board_size + 1)) // board_size
        side = board_size * self.cell + self.GAP * (board_size + 1)
        self.board_rect = pygame.Rect(self.BOARD_LEFT, self.BOARD_TOP, side, side)

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

    def current_card_cell_rect(self, row_index: int, col_index: int) -> pygame.Rect:
        pitch = self.CARD_CELL + self.CARD_GAP
        x, y = self.CARD_ORIGIN
        return pygame.Rect(
            x + col_index * pitch, y + row_index * pitch, self.CARD_CELL, self.CARD_CELL
        )

    def next_card_cell_rect(
        self, index: int, card_size: int, row_index: int, col_index: int
    ) -> pygame.Rect:
        """Cell of the `index`-th upcoming card (0 = the one right after the current)."""
        pitch = self.NEXT_CELL + self.NEXT_GAP
        card_width = card_size * self.NEXT_CELL + (card_size - 1) * self.NEXT_GAP
        x, y = self.NEXT_ORIGIN
        x += index * (card_width + self.NEXT_SPACING)
        return pygame.Rect(
            x + col_index * pitch, y + row_index * pitch, self.NEXT_CELL, self.NEXT_CELL
        )
