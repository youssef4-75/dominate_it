"""Stateless drawing functions (surface in, pixels out)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import pygame

from core import Game, MoveResult, Player, Position
from ui.messages import describe_move, describe_outcome, describe_start
from ui.pygame_ui.layout import Layout
from ui.pygame_ui.theme import (
    BACKGROUND, BUTTON, BUTTON_HOVER, EMPTY_CELL, MUTED, PANEL, PLAYER_COLORS,
    TEXT, WHITE, WINDOW_SIZE, Fonts,
)

CELL_RADIUS = 8


def draw_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    pos: Tuple[int, int],
    color: Tuple[int, int, int] = TEXT,
    anchor: str = "topleft",
) -> None:
    image = font.render(text, True, color)
    surface.blit(image, image.get_rect(**{anchor: pos}))


def draw_marker(surface: pygame.Surface, center: Tuple[int, int], size: int = 6) -> None:
    """Small white diamond: the card's center."""
    x, y = center
    points = [(x, y - size), (x + size, y), (x, y + size), (x - size, y)]
    pygame.draw.polygon(surface, WHITE, points)


@dataclass(frozen=True)
class Button:
    label: str
    rect: pygame.Rect
    value: object

    def draw(self, surface: pygame.Surface, fonts: Fonts, hovered: bool) -> None:
        pygame.draw.rect(surface, BUTTON_HOVER if hovered else BUTTON, self.rect, border_radius=12)
        pygame.draw.rect(surface, MUTED, self.rect, width=2, border_radius=12)
        draw_text(surface, fonts.normal, self.label, self.rect.center, TEXT, "center")


# -- game scene ---------------------------------------------------------------
def draw_scene(
    surface: pygame.Surface,
    fonts: Fonts,
    layout: Layout,
    game: Game,
    last_move: Optional[MoveResult],
) -> None:
    width = WINDOW_SIZE[0]
    surface.fill(BACKGROUND)
    draw_text(surface, fonts.title, "GRID COLOR WAR", (width // 2, 26), TEXT, "center")
    _draw_scores(surface, fonts, game)
    _draw_board(surface, layout, game)
    if not game.is_over:
        _draw_card(surface, fonts, layout, game)
        message = describe_start(game) if last_move is None else describe_move(last_move)
        for i, line in enumerate(message.splitlines()):
            draw_text(surface, fonts.small, line.strip(), (190, 606 + i * 24))
        draw_text(
            surface, fonts.small,
            "Click a cell to stamp the card   |   Esc: quit to home",
            (width // 2, WINDOW_SIZE[1] - 20), MUTED, "center",
        )


def _draw_scores(surface: pygame.Surface, fonts: Fonts, game: Game) -> None:
    width, box_w, box_h, top = WINDOW_SIZE[0], 170, 58, 50
    scores = game.scores()
    boxes = {
        Player.RED: pygame.Rect(24, top, box_w, box_h),
        Player.BLUE: pygame.Rect(width - 24 - box_w, top, box_w, box_h),
    }
    for player, rect in boxes.items():
        color = PLAYER_COLORS[player]
        active = player is game.current_player and not game.is_over
        pygame.draw.rect(surface, PANEL, rect, border_radius=10)
        pygame.draw.rect(surface, color, rect, width=3 if active else 1, border_radius=10)
        draw_text(surface, fonts.small, player.name, (rect.x + 14, rect.y + 9), color)
        draw_text(surface, fonts.big, str(scores[player]), (rect.x + 14, rect.y + 27))
        draw_text(surface, fonts.small, "cells", (rect.right - 14, rect.centery), MUTED, "midright")
    draw_text(surface, fonts.small, "Turns left", (width // 2, top + 14), MUTED, "center")
    draw_text(
        surface, fonts.normal, f"{game.turns_left} / {game.config.total_turns}",
        (width // 2, top + 38), TEXT, "center",
    )


def _draw_board(surface: pygame.Surface, layout: Layout, game: Game) -> None:
    pygame.draw.rect(surface, PANEL, layout.board_rect, border_radius=12)
    for row, cells in enumerate(game.grid):
        for col, cell in enumerate(cells):
            color = PLAYER_COLORS[cell] if cell is not None else EMPTY_CELL
            pygame.draw.rect(
                surface, color, layout.cell_rect(Position(row, col)), border_radius=CELL_RADIUS
            )


def _draw_card(surface: pygame.Surface, fonts: Fonts, layout: Layout, game: Game) -> None:
    card, player = game.current_card, game.current_player
    x, y = Layout.CARD_ORIGIN
    draw_text(surface, fonts.small, f"{player.name}'s card", (x, y - 24), PLAYER_COLORS[player])
    for i, d_row in enumerate(range(-card.radius, card.radius + 1)):
        for j, d_col in enumerate(range(-card.radius, card.radius + 1)):
            rect = layout.card_cell_rect(i, j)
            colored = Position(d_row, d_col) in card.offsets
            pygame.draw.rect(
                surface, PLAYER_COLORS[player] if colored else EMPTY_CELL, rect, border_radius=6
            )
            if d_row == 0 and d_col == 0:
                draw_marker(surface, rect.center, 5)


def draw_preview(
    surface: pygame.Surface, layout: Layout, game: Game, hovered: Optional[Position]
) -> None:
    """Translucent preview of where the card would paint, under the mouse."""
    if hovered is None or game.is_over:
        return
    color = PLAYER_COLORS[game.current_player]
    for position in game.painted_cells(hovered):
        rect = layout.cell_rect(position)
        tile = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(tile, (*color, 170), tile.get_rect(), border_radius=CELL_RADIUS)
        surface.blit(tile, rect.topleft)
        pygame.draw.rect(surface, WHITE, rect, width=2, border_radius=CELL_RADIUS)
    draw_marker(surface, layout.cell_rect(hovered).center)


def draw_game_over(surface: pygame.Surface, fonts: Fonts, layout: Layout, game: Game) -> None:
    overlay = pygame.Surface(layout.board_rect.size, pygame.SRCALPHA)
    overlay.fill((10, 12, 16, 210))
    surface.blit(overlay, layout.board_rect.topleft)

    cx, cy = layout.board_rect.center
    scores = game.scores()
    winner = game.winner()
    draw_text(surface, fonts.title, "GAME OVER", (cx, cy - 70), TEXT, "center")
    draw_text(surface, fonts.title, str(scores[Player.RED]),
              (cx - 60, cy), PLAYER_COLORS[Player.RED], "center")
    draw_text(surface, fonts.title, "-", (cx, cy), MUTED, "center")
    draw_text(surface, fonts.title, str(scores[Player.BLUE]),
              (cx + 60, cy), PLAYER_COLORS[Player.BLUE], "center")
    draw_text(surface, fonts.big, describe_outcome(game), (cx, cy + 70),
              PLAYER_COLORS[winner] if winner else TEXT, "center")
