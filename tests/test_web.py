"""Web UI tests: the API through FastAPI's TestClient. Skipped without fastapi/httpx."""
import random

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from core import (  # noqa: E402
    SETTINGS, Game, GameConfig, Position, RuleSet, new_game, players_for,
)
from tests.helpers import FixedCardSource, card  # noqa: E402
from ui.web import create_app  # noqa: E402
from ui.web.session import SessionStore  # noqa: E402
from ui.web.view import game_to_dict  # noqa: E402

DOT = card((0, 0))
FULL = card(*[(r, c) for r in (-1, 0, 1) for c in (-1, 0, 1)])
ROW0 = card((-1, -1), (-1, 0), (-1, 1))
ROW1 = card((0, -1), (0, 0), (0, 1))
ROW2 = card((1, -1), (1, 0), (1, 1))


def seeded(seed=1):
    return lambda config: new_game(config, random.Random(seed))


def fixed(*cards):
    return lambda config: Game(config, FixedCardSource(*cards))


def client(factory=None, default=None, **kw):
    return TestClient(create_app(factory or seeded(), default, **kw))


def create(c, config=None):
    response = c.post("/api/games", json={"config": config} if config is not None else None)
    assert response.status_code == 201, response.text
    return response.json()


def move(c, game_id, row, col):
    return c.post(f"/api/games/{game_id}/moves", json={"row": row, "col": col})


# ---------------------------------------------------------------- basic game flow
def test_new_game_state_has_everything_the_page_needs():
    state = create(client())
    assert state["size"] == 5 and len(state["grid"]) == 5
    assert all(cell is None for row in state["grid"] for cell in row)
    assert state["players"] == [{"name": "RED", "color": "#e24848"}, {"name": "BLUE", "color": "#4285e6"}]
    assert state["current_player"] == "RED"
    assert state["scores"] == {"RED": 0, "BLUE": 0}
    assert state["turns_left"] == state["total_turns"] == 50
    assert len(state["current_card"]["offsets"]) == 4
    assert len(state["upcoming_cards"]) == 2
    assert state["line_streak"] == 0 and state["line_streak_limit"] == 3
    assert state["last_move"] is None and state["is_over"] is False
    assert state["winners"] == [] and state["winner"] is None
    assert state["message"] == ["Game start! RED begins."]
    assert state["config"]["num_players"] == 2


def test_play_a_move_updates_the_state_and_gives_a_message():
    c = client()
    game_id = create(c)["id"]
    state = move(c, game_id, 2, 2).json()
    assert state["current_player"] == "BLUE"
    assert state["scores"]["RED"] == 4 and state["turns_left"] == 49
    assert state["last_move"]["player"] == "RED" and state["last_move"]["next_player"] == "BLUE"
    assert state["last_move"]["row"] == 2 and state["last_move"]["col"] == 2
    assert state["message"][0].startswith("RED played at row 3, col 3")
    assert c.get(f"/api/games/{game_id}").json() == state  # state is kept on the server


def test_invalid_moves_are_rejected_without_changing_the_game():
    c = client()
    game_id = create(c)["id"]
    for row, col in [(5, 0), (0, -1), (99, 99)]:
        response = move(c, game_id, row, col)
        assert response.status_code == 400 and "outside" in response.json()["detail"]
    assert c.post(f"/api/games/{game_id}/moves", json={"row": "x", "col": 1}).status_code == 422
    assert c.get(f"/api/games/{game_id}").json()["turns_left"] == 50


def test_unknown_game_is_404_and_delete_forgets_the_game():
    c = client()
    assert c.get("/api/games/nope").status_code == 404
    assert move(c, "nope", 0, 0).status_code == 404
    game_id = create(c)["id"]
    assert c.delete(f"/api/games/{game_id}").status_code == 204
    assert c.get(f"/api/games/{game_id}").status_code == 404
    assert c.delete(f"/api/games/{game_id}").status_code == 204  # idempotent


def test_a_whole_match_through_the_api():
    c = client()
    game_id = create(c)["id"]
    for _ in range(50):
        state = move(c, game_id, 2, 2).json()
    assert state["is_over"] and state["turns_left"] == 0
    assert state["outcome"] and set(state["winners"]) <= {"RED", "BLUE"}
    response = move(c, game_id, 2, 2)  # the match is over
    assert response.status_code == 400 and "over" in response.json()["detail"]


# ---------------------------------------------------------------- settings of each game
def test_the_settings_endpoint_describes_parameters_rules_and_defaults():
    c = client(default=GameConfig(total_turns=33))
    schema = c.get("/api/settings").json()
    assert [p["key"] for p in schema["parameters"]] == [s.key for s in SETTINGS]
    assert schema["defaults"]["total_turns"] == 33 and schema["defaults"]["num_players"] == 2
    rules = {r["name"]: r for r in schema["rules"]}
    assert rules["line_bonus"]["enabled"] and not rules["full_board_flip"]["enabled"]
    assert rules["line_streak_wipe"]["option_specs"][0]["key"] == "limit"
    assert rules["full_board_win"]["option_specs"][0]["choices"] == ["most_cells", "mover"]
    assert all(r["description"] for r in rules.values())


def test_each_game_has_its_own_configuration():
    c = client()
    a = create(c, {"num_players": 3, "total_turns": 12, "rules": {"enabled": ["line_bonus"]}})
    b = create(c, {"board_size": 7, "diagonals_count": False})
    assert [p["name"] for p in a["players"]] == ["RED", "BLUE", "GREEN"]
    assert a["total_turns"] == 12 and a["rules"] == ["line_bonus"] and a["size"] == 5
    assert len(b["players"]) == 2 and b["size"] == 7 and b["total_turns"] == 50
    assert b["config"]["diagonals_count"] is False
    assert c.get(f"/api/games/{a['id']}").json()["config"]["num_players"] == 3  # unchanged by b


def test_a_game_without_a_config_uses_the_server_defaults():
    c = client(default=GameConfig(players=players_for(4), total_turns=20))
    state = create(c)
    assert len(state["players"]) == 4 and state["total_turns"] == 20
    assert c.post("/api/games", json={}).json()["total_turns"] == 20
    assert create(c, {"total_turns": 8})["total_turns"] == 8  # a partial config keeps the rest


@pytest.mark.parametrize("bad, message", [
    ({"num_players": 9}, "between"),
    ({"board_size": "big"}, "whole number"),
    ({"unknown": 1}, "Unknown setting"),
    ({"rules": {"enabled": ["nope"]}}, "Unknown rule"),
    ({"rules": {"options": {"line_streak_wipe": {"limit": 0}}}}, ">= 1"),
])
def test_an_invalid_configuration_is_refused_with_a_readable_message(bad, message):
    c = client()
    response = c.post("/api/games", json={"config": bad})
    assert response.status_code == 400 and message in response.json()["detail"]


# ---------------------------------------------------------------- several players
def test_three_players_take_turns_through_the_api():
    c = client()
    state = create(c, {"num_players": 3})
    seen = []
    for i in range(6):
        seen.append(state["current_player"])
        state = move(c, state["id"], i % 5, 0).json()
    assert seen == ["RED", "BLUE", "GREEN", "RED", "BLUE", "GREEN"]
    assert set(state["scores"]) == {"RED", "BLUE", "GREEN"}
    assert state["last_move"]["next_player"] == state["current_player"]


# ---------------------------------------------------------------- rules through the API
def test_a_penalty_is_visible_in_the_state():
    cfg = GameConfig(board_size=3, total_turns=10, rules=RuleSet.of("full_board_flip"))
    c = client(fixed(FULL, DOT), cfg)
    state = move(c, create(c)["id"], 1, 1).json()
    assert state["last_move"]["events"] == ["board_flipped"]
    assert state["scores"] == {"RED": 0, "BLUE": 9}
    assert state["current_player"] == "BLUE" and not state["is_over"]
    assert any("switches to BLUE" in line for line in state["message"])


def test_filling_the_grid_alone_wins_immediately_through_the_api():
    cfg = GameConfig(board_size=3, total_turns=10)  # default rules include full_board_win
    c = client(fixed(FULL, DOT), cfg)
    state = move(c, create(c)["id"], 1, 1).json()
    assert state["is_over"] and state["winner"] == "RED" and state["winners"] == ["RED"]
    assert state["outcome"] == "RED wins!" and state["turns_left"] == 9
    assert state["upcoming_cards"] == []
    assert any("wins immediately" in line for line in state["message"])
    assert move(c, state["id"], 0, 0).status_code == 400


def test_a_grid_covered_by_several_players_ends_the_game_through_the_api():
    cfg = GameConfig(board_size=3, total_turns=30, players=players_for(3), rules=RuleSet.of("full_board_win"))
    c = client(fixed(ROW0, ROW1, ROW2), cfg)
    game_id = create(c)["id"]
    for _ in range(3):
        state = move(c, game_id, 1, 1).json()
    assert state["is_over"] and state["turns_left"] == 27
    assert state["scores"] == {"RED": 3, "BLUE": 3, "GREEN": 3}
    assert state["outcome"] == "It's a draw!" and sorted(state["winners"]) == ["BLUE", "GREEN", "RED"]
    assert any("grid is full" in line for line in state["message"])


def test_the_state_lists_the_rules_and_the_card_note():
    rules = RuleSet.of("catch_up_cards").with_options("catch_up_cards", gap=2)
    cfg = GameConfig(board_size=5, total_turns=20, rules=rules)
    base_for_blue = card((-1, 0), (0, 1), (1, -1), (1, 1))
    c = client(fixed(FULL, base_for_blue, DOT), cfg)
    created = create(c)
    assert created["rules"] == ["catch_up_cards"] and created["current_card"]["note"] == ""
    state = move(c, created["id"], 1, 1).json()  # RED paints 9: BLUE is far behind
    assert "boost" in state["current_card"]["note"].lower()


# ---------------------------------------------------------------- view model and plumbing
def test_view_model_shapes():
    cfg = GameConfig()
    game = new_game(cfg, random.Random(0))
    last = game.play(Position(2, 2))
    state = game_to_dict("abc", game, last)
    assert sum(cell == "RED" for row in state["grid"] for cell in row) == 4
    assert state["last_move"]["changed"] and isinstance(state["last_move"]["changed"][0], list)
    assert state["current_card"]["size"] == 3


def test_old_sessions_are_evicted():
    store = SessionStore(seeded(), max_sessions=2)
    first, second, third = (store.create(GameConfig()) for _ in range(3))
    with pytest.raises(KeyError):
        store.get(first.id)
    assert store.get(second.id) and store.get(third.id)


def test_page_and_static_files_are_served():
    c = client()
    page = c.get("/")
    assert page.status_code == 200 and "GRID COLOR WAR" in page.text
    assert "/static/app.js" in page.text and 'id="settings"' in page.text
    assert c.get("/static/app.js").status_code == 200
    assert c.get("/static/style.css").status_code == 200


def test_main_wires_the_web_app(monkeypatch):
    import main

    app = main.build_web_app(GameConfig(players=players_for(3)))
    web = TestClient(app)
    assert len(web.post("/api/games").json()["players"]) == 3  # the server default
    assert len(web.post("/api/games", json={"config": {"num_players": 2}}).json()["players"]) == 2

    started = {}
    monkeypatch.setattr("uvicorn.run", lambda app, **kw: started.update(kw))
    main.main(["--ui", "web", "--port", "9001", "--only", "line_bonus", "--players", "4"])
    assert started["port"] == 9001 and started["host"] == "127.0.0.1"
