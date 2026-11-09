"""Server-side game sessions (in memory).

The browser owns the loop on the web (it sends a click when the user clicks),
so instead of the blocking Renderer / Menu / MoveSelector interfaces, the
server exposes a `GameSession`: "give me the state" / "play this position".
"""
from __future__ import annotations

import secrets
import threading
from collections import OrderedDict
from typing import Any, Callable, Dict, Optional

from core import Game, GameConfig, MoveResult, Position
from ui.web.view import game_to_dict


class GameSession:
    def __init__(self, session_id: str, game: Game) -> None:
        self.id = session_id
        self._game = game
        self._last_move: Optional[MoveResult] = None
        self._lock = threading.Lock()  # requests run in a thread pool

    def state(self) -> Dict[str, Any]:
        with self._lock:
            return game_to_dict(self.id, self._game, self._last_move)

    def play(self, position: Position) -> Dict[str, Any]:
        """Play the current card at `position`. Raises InvalidMoveError."""
        with self._lock:
            self._last_move = self._game.play(position)
            return game_to_dict(self.id, self._game, self._last_move)


class SessionStore:
    """Keeps the most recently used sessions; the oldest ones are dropped."""

    def __init__(self, game_factory: Callable[[GameConfig], Game], max_sessions: int = 500) -> None:
        self._game_factory = game_factory
        self._max_sessions = max_sessions
        self._sessions: "OrderedDict[str, GameSession]" = OrderedDict()
        self._lock = threading.Lock()

    def create(self, config: GameConfig) -> GameSession:
        """A new game with its OWN configuration."""
        session = GameSession(secrets.token_urlsafe(9), self._game_factory(config))
        with self._lock:
            self._sessions[session.id] = session
            while len(self._sessions) > self._max_sessions:
                self._sessions.popitem(last=False)
        return session

    def get(self, session_id: str) -> GameSession:
        """Raises KeyError if unknown (or already dropped)."""
        with self._lock:
            session = self._sessions[session_id]
            self._sessions.move_to_end(session_id)
            return session

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None
