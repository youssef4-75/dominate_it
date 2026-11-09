"""Core game logic. Depends on nothing else in the project."""
from core.board import Board
from core.card import Card, CardSource, RandomCardSource
from core.config import SETTINGS, GameConfig, Setting
from core.errors import InvalidMoveError
from core.game import Game, new_game
from core.models import (
    MAX_PLAYERS, MIN_PLAYERS, PALETTE, Cell, Grid, MoveResult, Player, Position, RuleEvent,
    players_for,
)
from core.rules import (
    CardContext, CatchUpCards, FullBoardFlip, FullBoardWin, LineBonus, LineStreakWipe,
    MoveContext, Option, Rule, RuleSet,
)

__all__ = [
    "Board", "Card", "CardSource", "RandomCardSource", "GameConfig", "Setting", "SETTINGS",
    "InvalidMoveError", "Game", "new_game", "Cell", "Grid", "MoveResult", "Player", "Position",
    "RuleEvent", "PALETTE", "MIN_PLAYERS", "MAX_PLAYERS", "players_for",
    "CardContext", "CatchUpCards", "FullBoardFlip", "FullBoardWin", "LineBonus",
    "LineStreakWipe", "MoveContext", "Option", "Rule", "RuleSet",
]
