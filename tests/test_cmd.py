import random

import pytest

from core import Game, GameConfig, Position, RandomCardSource, RuleSet
from main import build_application
from players import MatchAborted
from ui import AfterMatchChoice, MainChoice
from ui.cmd import CmdHumanPlayer, CmdMenu, CmdRenderer
from ui.cmd.human_player import parse_position


def test_parse_position():
    assert parse_position("3 4", 5) == Position(2, 3)
    assert parse_position("3,4", 5) == Position(2, 3)
    for bad in ("", "3", "a b", "0 1", "6 1", "1 2 3", "-1 2"):
        assert parse_position(bad, 5) is None


def new_game(config=None):
    config = config or GameConfig()
    return Game(config, RandomCardSource.from_config(config, random.Random(0)))


def test_human_retries_until_valid_input():
    answers = iter(["nope", "9 9", " 3,4 "])
    printed = []
    player = CmdHumanPlayer(lambda _: next(answers), printed.append)
    assert player.choose_move(new_game()) == Position(2, 3)
    assert len(printed) == 2  # two error messages


def test_human_can_quit():
    player = CmdHumanPlayer(lambda _: "Q", lambda _: None)
    with pytest.raises(MatchAborted):
        player.choose_move(new_game())


def test_menu_choices():
    answers = iter(["x", "1"])
    menu = CmdMenu(lambda _: next(answers), lambda _: None, lambda: None)
    assert menu.ask_main_choice() is MainChoice.PLAY
    assert CmdMenu(lambda _: "r", lambda _: None).ask_after_match() is AfterMatchChoice.REPLAY
    assert CmdMenu(lambda _: "h", lambda _: None).ask_after_match() is AfterMatchChoice.HOME


def test_renderer_prints_without_crashing():
    lines = []
    renderer = CmdRenderer(lines.append, lambda: None)
    game = new_game()
    renderer.render_game(game, None)
    result = game.play(Position(2, 2))
    renderer.render_game(game, result)
    renderer.render_game_over(game)
    text = "\n".join(lines)
    assert "Turns left: 49 / 50" in text and "GAME OVER" in text


def test_whole_app_with_scripted_console():
    """Play a complete 50-turn match through the real glue + cmd components."""
    from application import Application
    from core import Player
    from match_runner import MatchRunner

    answers = iter(["1"] + ["3 3"] * 50 + ["h", "2"])
    ask = lambda _="": next(answers)
    out = []
    human = CmdHumanPlayer(ask, out.append)
    runner = MatchRunner(
        new_game,
        CmdRenderer(out.append, lambda: None),
        human,
    )
    Application(CmdMenu(ask, out.append, lambda: None), runner).run()
    text = "\n".join(out)
    assert "GAME OVER" in text and "Bye!" in text


def test_main_wires_the_console_ui():
    assert build_application(ui="cmd") is not None


def test_main_uses_pygame_by_default_and_cmd_on_request(monkeypatch):
    import main

    seen = []

    class FakeApp:
        def run(self):
            pass

    def fake_build(config=None, ui=None):
        seen.append(ui)
        return FakeApp()

    monkeypatch.setattr(main, "build_application", fake_build)
    main.main([])
    main.main(["--ui", "cmd"])
    assert seen == ["pygame", "cmd"]


def test_rule_switches_reach_the_game_config(monkeypatch, capsys):
    import main

    configs = []

    class FakeApp:
        def run(self):
            pass

    monkeypatch.setattr(main, "build_application", lambda config=None, ui=None: configs.append(config) or FakeApp())
    main.main(["--ui", "cmd", "--disable", "catch_up_cards", "--enable", "full_board_flip",
               "--set", "line_streak_wipe.limit=2"])
    rules = configs[0].rules
    assert not rules.is_enabled("catch_up_cards") and rules.is_enabled("full_board_flip")
    assert rules.option("line_streak_wipe", "limit") == 2


def test_build_ruleset_from_command_line_values():
    from main import build_ruleset

    assert build_ruleset().names == RuleSet.default().names
    assert build_ruleset(only=["line_bonus,full_board_win"]).names == ("full_board_win", "line_bonus")
    assert build_ruleset(only=["none"]).names == ()
    assert build_ruleset(only=["none"], enable=["line_bonus"]).names == ("line_bonus",)
    assert build_ruleset(disable=["catch_up_cards", "line_bonus"]).names == ("full_board_win", "line_streak_wipe")
    assert build_ruleset(settings=["catch_up_cards.gap=4"]).option("catch_up_cards", "gap") == 4
    for bad in (dict(enable=["nope"]), dict(settings=["line_bonus"]), dict(settings=["line_bonus.x=1"])):
        with pytest.raises(ValueError):
            build_ruleset(**bad)


def test_list_rules_and_bad_rule_names_on_the_command_line(capsys):
    import main

    main.main(["--list-rules", "--disable", "line_bonus"])
    out = capsys.readouterr().out
    assert "[x] full_board_win" in out and "[ ] line_bonus" in out and "[ ] full_board_flip" in out
    with pytest.raises(SystemExit):
        main.main(["--enable", "nope", "--list-rules"])
