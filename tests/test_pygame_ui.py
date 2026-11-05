"""pygame UI tests, run headless (SDL dummy video driver). Skipped without pygame."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import random  # noqa: E402

import pytest  # noqa: E402

pygame = pytest.importorskip("pygame")

from application import Application  # noqa: E402
from core import Game, GameConfig, Player, Position, RandomCardSource  # noqa: E402
from match_runner import MatchRunner, MatchStatus  # noqa: E402
from players import MatchAborted  # noqa: E402
from ui import AfterMatchChoice, MainChoice  # noqa: E402
from ui.pygame_ui import (  # noqa: E402
    PygameHumanPlayer, PygameMenu, PygameRenderer, PygameWindow,
)
from ui.pygame_ui.layout import Layout  # noqa: E402
from ui.pygame_ui.menu import after_match_buttons, main_menu_buttons  # noqa: E402


@pytest.fixture
def window():
    w = PygameWindow(fps=1000)
    yield w
    w.close()


def new_game(turns=50):
    config = GameConfig(total_turns=turns)
    return Game(config, RandomCardSource.from_config(config, random.Random(0)))


def click(pos):
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))


def key(k):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k))


def test_layout_maps_pixels_to_cells_and_back():
    layout = Layout(5)
    for r in range(5):
        for c in range(5):
            pos = Position(r, c)
            assert layout.cell_at(layout.cell_rect(pos).center) == pos
    assert layout.cell_at((0, 0)) is None
    assert layout.cell_at((10_000, 10_000)) is None


def test_human_returns_the_clicked_cell(window):
    game = new_game()
    PygameRenderer(window).render_game(game, None)
    click(Layout(5).cell_rect(Position(1, 3)).center)
    assert PygameHumanPlayer(window).choose_move(game) == Position(1, 3)


def test_clicks_outside_the_board_are_ignored(window):
    game = new_game()
    PygameRenderer(window).render_game(game, None)
    click((5, 5))
    click(Layout(5).cell_rect(Position(4, 4)).center)
    assert PygameHumanPlayer(window).choose_move(game) == Position(4, 4)


def test_escape_aborts(window):
    game = new_game()
    PygameRenderer(window).render_game(game, None)
    key(pygame.K_ESCAPE)
    with pytest.raises(MatchAborted):
        PygameHumanPlayer(window).choose_move(game)


def test_closing_the_window_aborts_and_quits(window):
    game = new_game()
    PygameRenderer(window).render_game(game, None)
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    with pytest.raises(MatchAborted):
        PygameHumanPlayer(window).choose_move(game)
    assert window.closed
    assert PygameMenu(window).ask_main_choice() is MainChoice.QUIT


def test_main_menu_by_click_and_key(window):
    menu = PygameMenu(window)
    play, quit_ = main_menu_buttons()
    click(play.rect.center)
    assert menu.ask_main_choice() is MainChoice.PLAY
    click(quit_.rect.center)
    assert menu.ask_main_choice() is MainChoice.QUIT
    key(pygame.K_RETURN)
    assert menu.ask_main_choice() is MainChoice.PLAY


def test_after_match_menu(window):
    menu = PygameMenu(window)
    replay, home = after_match_buttons()
    click(replay.rect.center)
    assert menu.ask_after_match() is AfterMatchChoice.REPLAY
    click(home.rect.center)
    assert menu.ask_after_match() is AfterMatchChoice.HOME
    key(pygame.K_r)
    assert menu.ask_after_match() is AfterMatchChoice.REPLAY


class ClickingRenderer(PygameRenderer):
    """Test helper: 'plays' by clicking the middle cell after each render."""

    def render_game(self, game, last_move):
        super().render_game(game, last_move)
        if not game.is_over:
            click(Layout(game.size).cell_rect(Position(2, 2)).center)


def test_full_match_and_app_flow_through_pygame(window):
    human = PygameHumanPlayer(window)
    runner = MatchRunner(
        lambda: new_game(turns=50),
        ClickingRenderer(window),
        {Player.RED: human, Player.BLUE: human},
    )
    menu = PygameMenu(window)
    play, _ = main_menu_buttons()
    _, home = after_match_buttons()
    click(play.rect.center)  # home page -> Play

    # The match ends, then "Home" is clicked, then the home page's Quit key.
    outcome = {}
    original = menu.ask_after_match

    def ask_after_match():
        click(home.rect.center)
        outcome["status"] = "asked"
        return original()

    menu.ask_after_match = ask_after_match
    original_main = menu.ask_main_choice
    calls = {"n": 0}

    def ask_main():
        calls["n"] += 1
        if calls["n"] == 2:
            key(pygame.K_ESCAPE)
        return original_main()

    menu.ask_main_choice = ask_main
    Application(menu, runner).run()
    assert outcome["status"] == "asked"
    assert window.closed  # show_goodbye released pygame


def test_main_builds_the_pygame_application():
    from main import build_application

    assert build_application(ui="pygame") is not None
    pygame.quit()  # the window opened by the builder
