"""Stateless drawing functions (surface in, pixels out)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import pygame

from core import Card, Game, MoveResult, Position
from ui.messages import describe_move, describe_outcome, describe_rules, describe_start
from ui.pygame_ui.layout import Layout
from ui.pygame_ui.theme import (
    BACKGROUND, BUTTON, BUTTON_HOVER, DARK, EMPTY_CELL, MUTED, NEUTRAL_CARD, PANEL,
    TEXT, WARNING, WHITE, WINDOW_SIZE, Fonts,
)

CELL_RADIUS = 8
MESSAGE_LINE_HEIGHT = 24


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


def wrap_lines(font: pygame.font.Font, text: str, max_width: int) -> List[str]:
    """Split text into lines that fit `max_width` (explicit newlines are kept)."""
    lines: List[str] = []
    for paragraph in text.splitlines():
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}".strip()
            if current and font.size(candidate)[0] > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
    return lines


def draw_marker(
    surface: pygame.Surface, center: Tuple[int, int], size: int = 6,
    color: Tuple[int, int, int] = WHITE,
) -> None:
    """Small diamond: the card's center."""
    x, y = center
    pygame.draw.polygon(surface, color, [(x, y - size), (x + size, y), (x, y + size), (x - size, y)])


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
    width, height = WINDOW_SIZE
    surface.fill(BACKGROUND)
    draw_text(surface, fonts.title, "GRID COLOR WAR", (width // 2, 22), TEXT, "center")
    _draw_scores(surface, fonts, layout, game)
    _draw_board(surface, layout, game)
    _draw_message(surface, fonts, layout, game, last_move)
    if not game.is_over:
        _draw_current_card(surface, fonts, layout, game)
        _draw_upcoming_cards(surface, fonts, layout, game)
        _draw_streak(surface, fonts, layout, game)
        _draw_rules(surface, fonts, game)
        draw_text(
            surface, fonts.small, "Click a cell to stamp the card   |   Esc: quit to home",
            (width // 2, height - 18), MUTED, "center",
        )


def _draw_scores(surface: pygame.Surface, fonts: Fonts, layout: Layout, game: Game) -> None:
    """One box per player (2 to 6), in turn order; the active player has a thick border."""
    board = layout.board_rect
    scores = game.scores()
    count, gap, top, height = len(game.players), 8, 70, 46
    box_w = (board.width - gap * (count - 1)) // count
    wide = box_w >= 150
    name_font = fonts.small if box_w >= 100 else fonts.tiny
    draw_text(
        surface, fonts.small, f"Turns left: {game.turns_left} / {game.config.total_turns}",
        (board.centerx, 52), MUTED, "center",
    )
    for index, player in enumerate(game.players):
        rect = pygame.Rect(board.left + index * (box_w + gap), top, box_w, height)
        active = player == game.current_player and not game.is_over
        pygame.draw.rect(surface, PANEL, rect, border_radius=10)
        pygame.draw.rect(surface, player.color, rect, width=3 if active else 1, border_radius=10)
        draw_text(surface, name_font, player.name, (rect.x + 8, rect.y + 5), player.color)
        draw_text(surface, fonts.normal, str(scores[player]), (rect.x + 8, rect.y + 21))
        if wide:
            draw_text(surface, fonts.small, "cells", (rect.right - 10, rect.y + 31), MUTED, "midright")


def _draw_board(surface: pygame.Surface, layout: Layout, game: Game) -> None:
    pygame.draw.rect(surface, PANEL, layout.board_rect, border_radius=12)
    for row, cells in enumerate(game.grid):
        for col, cell in enumerate(cells):
            color = cell.color if cell is not None else EMPTY_CELL
            pygame.draw.rect(
                surface, color, layout.cell_rect(Position(row, col)), border_radius=CELL_RADIUS
            )


def _draw_message(
    surface: pygame.Surface, fonts: Fonts, layout: Layout, game: Game,
    last_move: Optional[MoveResult],
) -> None:
    """What just happened, under the board (wrapped to the board's width)."""
    if last_move is None:
        message = describe_start(game)
    else:
        message = describe_move(last_move)
    board = layout.board_rect
    y = board.bottom + 12
    for line in wrap_lines(fonts.small, message, board.width):
        draw_text(surface, fonts.small, line.strip(), (board.x, y))
        y += MESSAGE_LINE_HEIGHT


def _draw_card(
    surface: pygame.Surface,
    card: Card,
    color: Tuple[int, int, int],
    rect_of: Callable[[int, int], pygame.Rect],
    radius: int,
    marker_size: int,
    neutral: bool = False,
) -> None:
    for i, d_row in enumerate(range(-card.radius, card.radius + 1)):
        for j, d_col in enumerate(range(-card.radius, card.radius + 1)):
            rect = rect_of(i, j)
            colored = Position(d_row, d_col) in card.offsets
            pygame.draw.rect(surface, color if colored else EMPTY_CELL, rect, border_radius=radius)
            if d_row == 0 and d_col == 0:
                dark_marker = neutral and colored  # white would vanish on light gray
                draw_marker(surface, rect.center, marker_size, DARK if dark_marker else WHITE)


def _draw_current_card(surface: pygame.Surface, fonts: Fonts, layout: Layout, game: Game) -> None:
    player = game.current_player
    x, y = Layout.CARD_ORIGIN
    draw_text(surface, fonts.small, f"{player.name}'s card", (x, y - 28), player.color)
    _draw_card(
        surface, game.current_card, player.color,
        layout.current_card_cell_rect, radius=7, marker_size=6,
    )
    if game.current_card.note:  # set by a rule, e.g. catch-up boost / leader handicap
        _, note_y = Layout.CARD_NOTE_POS
        for line in wrap_lines(fonts.small, game.current_card.note, 280):
            draw_text(surface, fonts.small, line, (x, note_y), WARNING)
            note_y += MESSAGE_LINE_HEIGHT


def _draw_upcoming_cards(surface: pygame.Surface, fonts: Fonts, layout: Layout, game: Game) -> None:
    upcoming = game.upcoming_cards
    if not upcoming:
        return
    x, y = Layout.NEXT_ORIGIN
    draw_text(surface, fonts.small, "Coming next", (x, y - 28), MUTED)
    for index, card in enumerate(upcoming):
        def rect_of(i: int, j: int, index=index, size=card.size) -> pygame.Rect:
            return layout.next_card_cell_rect(index, size, i, j)

        _draw_card(surface, card, NEUTRAL_CARD, rect_of, radius=5, marker_size=4, neutral=True)


def _draw_streak(surface: pygame.Surface, fonts: Fonts, layout: Layout, game: Game) -> None:
    limit = game.line_streak_limit
    if limit is None:
        return
    streak = game.line_streak
    danger = streak > 0 and streak >= limit - 1
    draw_text(
        surface, fonts.small, f"Line streak: {streak} / {limit}",
        Layout.STREAK_POS, WARNING if danger else MUTED,
    )
    if danger:
        draw_text(
            surface, fonts.small, "One more line and you lose all your cells!",
            (Layout.STREAK_POS[0], Layout.STREAK_POS[1] + 24), WARNING,
        )


def _draw_rules(surface: pygame.Surface, fonts: Fonts, game: Game) -> None:
    x, y = Layout.RULES_POS
    for line in wrap_lines(fonts.small, describe_rules(game), 300):
        draw_text(surface, fonts.small, line, (x, y), MUTED)
        y += MESSAGE_LINE_HEIGHT


def draw_preview(
    surface: pygame.Surface, layout: Layout, game: Game, hovered: Optional[Position]
) -> None:
    """Translucent preview of where the card would paint, under the mouse."""
    if hovered is None or game.is_over:
        return
    color = game.current_player.color
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
    winners = game.winners()
    draw_text(surface, fonts.title, "GAME OVER", (cx, cy - 70), TEXT, "center")
    count = len(game.players)
    spacing = min(80, (layout.board_rect.width - 40) // count)
    for index, player in enumerate(game.players):
        x = cx + int((index - (count - 1) / 2) * spacing)
        draw_text(surface, fonts.title, str(scores[player]), (x, cy), player.color, "center")
    color = winners[0].color if len(winners) == 1 else TEXT
    for i, line in enumerate(wrap_lines(fonts.big, describe_outcome(game), layout.board_rect.width - 30)):
        draw_text(surface, fonts.big, line, (cx, cy + 62 + i * 30), color, "center")
