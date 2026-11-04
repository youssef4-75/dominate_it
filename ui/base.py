"""Interfaces every user interface (cmd, tkinter, pygame, pyplot...) implements."""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from core import Game, MoveResult


class MainChoice(Enum):
    PLAY = "play"
    QUIT = "quit"


class AfterMatchChoice(Enum):
    REPLAY = "replay"
    HOME = "home"


class Renderer(ABC):
    """How the game is displayed (output only)."""

    @abstractmethod
    def render_game(self, game: Game, last_move: Optional[MoveResult]) -> None:
        """Show the current state. `last_move` is None before the first move."""

    @abstractmethod
    def render_game_over(self, game: Game) -> None:
        """Show the final scores and the winner."""


class Menu(ABC):
    """How the player navigates between matches (home page)."""

    @abstractmethod
    def ask_main_choice(self) -> MainChoice: ...

    @abstractmethod
    def ask_after_match(self) -> AfterMatchChoice: ...

    @abstractmethod
    def show_goodbye(self) -> None: ...
