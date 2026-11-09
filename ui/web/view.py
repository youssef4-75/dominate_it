"""Game -> JSON-friendly dict: the "view model" sent to the browser.

The browser never sees `core` objects, only this plain data. Texts come from
`ui.messages`, so the wording is the same as in the console and pygame UIs.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core import SETTINGS, Card, Game, GameConfig, MoveResult
from ui.messages import describe_move, describe_outcome, describe_start


def _lines(text: str) -> List[str]:
    return [line.strip() for line in text.splitlines()]


def card_to_dict(card: Card) -> Dict[str, Any]:
    """`offsets` are [d_row, d_col] of the colored cells, relative to the center."""
    return {
        "size": card.size,
        "offsets": sorted([o.row, o.col] for o in card.offsets),
        "note": card.note,  # set by a rule (e.g. catch-up boost); "" if none
    }


def move_to_dict(result: MoveResult) -> Dict[str, Any]:
    return {
        "player": result.player.name,
        "next_player": result.next_player.name if result.next_player is not None else None,
        "row": result.position.row,
        "col": result.position.col,
        "changed": [[p.row, p.col] for p in result.changed_cells],
        "new_lines": list(result.new_lines),
        "bonus_turn": result.bonus_turn,
        "events": [event.code for event in result.events],
        "line_streak": result.line_streak,
        "message": _lines(describe_move(result)),
    }


def game_to_dict(
    game_id: str, game: Game, last_move: Optional[MoveResult]
) -> Dict[str, Any]:
    scores = game.scores()
    winners = game.winners() if game.is_over else ()
    return {
        "id": game_id,
        "size": game.size,
        "players": [{"name": p.name, "color": p.hex_color} for p in game.players],  # turn order
        "grid": [[cell.name if cell is not None else None for cell in row] for row in game.grid],
        "current_player": game.current_player.name,
        "scores": {player.name: scores[player] for player in game.players},
        "turns_left": game.turns_left,
        "total_turns": game.config.total_turns,
        "is_over": game.is_over,
        "winner": winners[0].name if len(winners) == 1 else None,
        "winners": [p.name for p in winners],
        "outcome": describe_outcome(game) if game.is_over else None,
        "current_card": card_to_dict(game.current_card),
        "upcoming_cards": [card_to_dict(card) for card in game.upcoming_cards],
        "line_streak": game.line_streak,
        "line_streak_limit": game.line_streak_limit,  # None if that rule is off
        "rules": list(game.rule_names),
        "config": game.config.to_dict(),  # what the settings form needs to replay the same game
        "last_move": move_to_dict(last_move) if last_move is not None else None,
        "message": _lines(describe_start(game) if last_move is None else describe_move(last_move)),
    }


def settings_schema(default: GameConfig) -> Dict[str, Any]:
    """Everything the browser needs to build the settings form (no rule is hard-coded in JS)."""
    return {
        "defaults": default.to_dict(),
        "parameters": [
            {"key": s.key, "label": s.label, "kind": s.kind, "min": s.minimum, "max": s.maximum, "step": s.step}
            for s in SETTINGS
        ],
        "rules": default.rules.describe(),
    }
