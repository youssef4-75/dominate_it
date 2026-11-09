"""The FastAPI application: thin HTTP layer over GameSession + the static page."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core import Game, GameConfig, InvalidMoveError, Position
from ui.web.session import GameSession, SessionStore
from ui.web.view import settings_schema

STATIC_DIR = Path(__file__).parent / "static"


class MoveIn(BaseModel):
    row: int  # 0-indexed
    col: int  # 0-indexed


class NewGameIn(BaseModel):
    # Settings of THIS game, as GameConfig.to_dict(): any subset, the rest is the default.
    config: Optional[Dict[str, Any]] = None


def create_app(
    game_factory: Callable[[GameConfig], Game],
    default_config: Optional[GameConfig] = None,
    max_sessions: int = 500,
) -> FastAPI:
    default_config = default_config or GameConfig()
    app = FastAPI(title="Grid Color War")
    store = SessionStore(game_factory, max_sessions)

    def find(game_id: str) -> GameSession:
        try:
            return store.get(game_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Unknown game (it may have expired).")

    @app.get("/api/settings")
    def get_settings():
        """The settings schema + defaults: the browser builds its settings form from this."""
        return settings_schema(default_config)

    @app.post("/api/games", status_code=201)
    def create_game(body: Optional[NewGameIn] = None):
        try:
            config = GameConfig.from_dict((body.config if body else None) or {}, base=default_config)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))
        return store.create(config).state()

    @app.get("/api/games/{game_id}")
    def get_game(game_id: str):
        return find(game_id).state()

    @app.post("/api/games/{game_id}/moves")
    def play_move(game_id: str, move: MoveIn):
        session = find(game_id)
        try:
            return session.play(Position(move.row, move.col))
        except InvalidMoveError as error:
            raise HTTPException(status_code=400, detail=str(error))

    @app.delete("/api/games/{game_id}", status_code=204)
    def delete_game(game_id: str):
        store.delete(game_id)
        return Response(status_code=204)

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
