"""pygame UI tests, run headless (SDL dummy video driver). Skipped without pygame."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import random  # noqa: E402

import pytest  # noqa: E402

pygame = pytest.importorskip("pygame")

from application import Application  # noqa: E402
from core import Game, GameConfig, Player, Position, RandomCardSource, RuleSet, players_for  # noqa: E402
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


def new_game(turns=50, players=2):
    config = GameConfig(total_turns=turns, players=players_for(players))
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

    def __init__(self, window):
        super().__init__(window)
        self.player_counts = []

    def render_game(self, game, last_move):
        super().render_game(game, last_move)
        self.player_counts.append(len(game.players))
        if not game.is_over:
            click(Layout(game.size).cell_rect(Position(2, 2)).center)


def test_the_renderer_draws_two_to_six_players_and_the_game_over_screen(window):
    renderer = PygameRenderer(window)
    for count in range(2, 7):
        game = new_game(turns=6, players=count)
        renderer.render_game(game, None)
        for i in range(6):
            last = game.play(Position(i % 5, i % 5))
            renderer.render_game(game, last)
        assert game.is_over
        renderer.render_game_over(game)  # does not raise whatever the number of players


def test_full_flow_home_settings_match_replay_home_quit(window):
    """Play (home) -> settings (Start) -> a 3-player match -> Home -> Quit."""
    renderer = ClickingRenderer(window)
    runner = MatchRunner(lambda cfg: Game(cfg, RandomCardSource.from_config(cfg, random.Random(0))),
                         renderer, PygameHumanPlayer(window))
    menu = PygameMenu(window)
    play, _ = main_menu_buttons()
    _, home = after_match_buttons()

    ask_main, ask_settings, ask_after = menu.ask_main_choice, menu.ask_game_config, menu.ask_after_match
    calls = {"main": 0}

    def main_choice():
        calls["main"] += 1
        if calls["main"] == 1:
            click(play.rect.center)  # first visit: Play
        else:
            key(pygame.K_ESCAPE)  # second visit: Quit
        return ask_main()

    def settings(current):
        key(pygame.K_RETURN)  # accept the proposed settings: Start game
        return ask_settings(current)

    def after_match():
        click(home.rect.center)
        return ask_after()

    menu.ask_main_choice, menu.ask_game_config, menu.ask_after_match = main_choice, settings, after_match
    start = GameConfig(players=players_for(3), total_turns=9)
    Application(menu, runner, start).run()

    assert set(renderer.player_counts) == {3} and len(renderer.player_counts) == 10  # 9 moves + final
    assert window.closed  # show_goodbye released pygame


def test_main_builds_the_pygame_application():
    from main import build_application

    assert build_application(ui="pygame") is not None
    pygame.quit()  # the window opened by the builder


# ---------------------------------------------------------------- the settings screen
from ui.pygame_ui import settings as S  # noqa: E402
from ui.pygame_ui.settings import SettingsScreen  # noqa: E402

PLAYERS, BOARD, TURNS, CELLS, PREVIEW, DIAGONALS = range(6)  # row order of core.SETTINGS


def param_rect(index):
    return pygame.Rect(S.LEFT_X, S.TOP + index * 50, S.LEFT_W, 42)


def minus(index):
    rect = param_rect(index)
    return (rect.right - 12 - 144 + 17, rect.y + 21)


def plus(index):
    rect = param_rect(index)
    return (rect.right - 12 - 144 + 110 + 17, rect.y + 21)


def diagonals_box():
    rect = param_rect(DIAGONALS)
    return (rect.right - 12 - 14, rect.y + 21)


# vertical position of each rule box (see settings._draw): 42 + 36 per option, 6 between boxes
RULE_Y = {"full_board_win": 116, "full_board_flip": 200, "line_streak_wipe": 248,
          "line_bonus": 332, "catch_up_cards": 380}


def rule_box(name):
    return (S.RIGHT_X + 26, RULE_Y[name] + 21)


def rule_option_plus(name):
    return (S.RIGHT_X + S.RIGHT_W - 12 - 144 + 110 + 17, RULE_Y[name] + 42 + 17)


def rule_option_minus(name):
    return (S.RIGHT_X + S.RIGHT_W - 12 - 144 + 17, RULE_Y[name] + 42 + 17)


WINNER_BUTTON = (S.RIGHT_X + S.RIGHT_W - 12 - 72, RULE_Y["full_board_win"] + 42 + 17)
BACK, DEFAULTS, START = (115, 658), (295, 658), (705, 658)


def run_settings(window, current, clicks=(), then=pygame.K_RETURN):
    """Post the clicks, then a key (Enter = Start, Esc = Back), and run the screen."""
    for position in clicks:
        click(position)
    if then is not None:
        key(then)
    return SettingsScreen(window).run(current)


def test_settings_start_from_the_current_settings_and_enter_starts(window):
    current = GameConfig(players=players_for(3), total_turns=60, board_size=6)
    assert run_settings(window, current) == current


def test_settings_steppers_and_checkboxes_change_the_game(window):
    config = run_settings(window, GameConfig(), clicks=[
        plus(PLAYERS), plus(PLAYERS),          # 2 -> 4 players
        minus(TURNS),                          # 50 -> 45 turns
        plus(BOARD),                           # 5 -> 6
        minus(PREVIEW), minus(PREVIEW),        # 2 -> 0 cards shown ahead
        diagonals_box(),                       # diagonals no longer count
        rule_box("line_bonus"),                # rule off
        rule_box("full_board_flip"),           # rule on
    ])
    assert [p.name for p in config.players] == ["RED", "BLUE", "GREEN", "YELLOW"]
    assert config.total_turns == 45 and config.board_size == 6 and config.preview_cards == 0
    assert config.diagonals_count is False
    assert not config.rules.is_enabled("line_bonus") and config.rules.is_enabled("full_board_flip")


def test_settings_rule_options_can_be_changed(window):
    config = run_settings(window, GameConfig(), clicks=[
        rule_option_plus("line_streak_wipe"), rule_option_plus("line_streak_wipe"),  # limit 3 -> 5
        rule_option_minus("catch_up_cards"),                                       # gap 10 -> 9
        WINNER_BUTTON,                                                             # most_cells -> mover
    ])
    assert config.rules.option("line_streak_wipe", "limit") == 5
    assert config.rules.option("catch_up_cards", "gap") == 9
    assert config.rules.option("full_board_win", "winner") == "mover"


def test_settings_values_stay_inside_their_limits(window):
    config = run_settings(window, GameConfig(), clicks=[minus(PLAYERS)] * 5 + [plus(CELLS)] * 12)
    assert len(config.players) == 2 and config.colored_cells == 9  # min players, max cells
    config = run_settings(window, GameConfig(), clicks=[plus(PLAYERS)] * 9)
    assert len(config.players) == 6


def test_options_of_a_disabled_rule_are_inert(window):
    config = run_settings(window, GameConfig(), clicks=[
        rule_box("line_streak_wipe"),             # off
        rule_option_plus("line_streak_wipe"),     # greyed out: ignored
    ])
    assert not config.rules.is_enabled("line_streak_wipe")
    assert config.rules.option("line_streak_wipe", "limit") == 3


def test_settings_defaults_button_restores_the_default_game(window):
    config = run_settings(window, GameConfig(), clicks=[plus(PLAYERS), rule_box("line_bonus"), DEFAULTS])
    assert config == GameConfig()


def test_settings_back_button_and_escape_give_nothing(window):
    assert run_settings(window, GameConfig(), clicks=[plus(PLAYERS), BACK], then=None) is None
    assert run_settings(window, GameConfig(), clicks=[plus(PLAYERS)], then=pygame.K_ESCAPE) is None


def test_settings_start_button_works_like_enter(window):
    config = run_settings(window, GameConfig(), clicks=[plus(PLAYERS), START], then=None)
    assert len(config.players) == 3


def test_closing_the_window_in_the_settings_gives_nothing(window):
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    assert SettingsScreen(window).run(GameConfig()) is None
    assert window.closed


def test_the_menu_opens_the_settings_screen(window):
    key(pygame.K_RETURN)
    current = GameConfig(players=players_for(4))
    assert PygameMenu(window).ask_game_config(current) == current


def test_the_settings_screen_draws_with_any_rule_selection(window):
    form = S._Form(GameConfig(rules=RuleSet.none()))
    SettingsScreen(window)._draw(form, "an error message", lambda: None, lambda: None)  # no crash
    form.load(GameConfig(players=players_for(6)))
    SettingsScreen(window)._draw(form, "", lambda: None, lambda: None)
