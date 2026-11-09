"""Composition root: the ONLY place that picks concrete implementations.

    python main.py                       # pygame window (default)
    python main.py --ui cmd              # console
    python main.py --ui web              # website at http://127.0.0.1:8000

Starting values of a game (the pygame and web UIs let you change them per game):
    python main.py --players 4 --board-size 7 --turns 80

Rules can be switched on/off from the command line, for any UI:
    python main.py --list-rules                       # what exists, what is on
    python main.py --disable catch_up_cards           # turn a rule off
    python main.py --enable full_board_flip --disable full_board_win
    python main.py --only line_bonus                  # ONLY these rules (--only none = plain game)
    python main.py --set line_streak_wipe.limit=2 --set catch_up_cards.gap=5

To plug in another interface or another kind of player (bot, socket, LLM...),
change `_build_ui` / the `selectors` mapping and nothing else.
"""
from __future__ import annotations

import argparse
from typing import List, Optional, Sequence, Tuple

from application import Application
from core import GameConfig, RuleSet, new_game, players_for
from match_runner import MatchRunner
from players import MoveSelector
from ui import Menu, Renderer

DEFAULT_UI = "pygame"
UI_CHOICES = ("pygame", "cmd", "web")


def _build_ui(ui: str) -> Tuple[Renderer, Menu, MoveSelector]:
    """Returns (renderer, menu, human move selector) for a local, blocking UI."""
    if ui == "pygame":
        # Imported lazily so console users don't need pygame installed.
        try:
            from ui.pygame_ui import (
                PygameHumanPlayer, PygameMenu, PygameRenderer, PygameWindow,
            )
        except ImportError as error:
            raise SystemExit(
                "The pygame interface needs pygame:  pip install pygame\n"
                "(or play in the console:  python main.py --ui cmd)"
            ) from error

        window = PygameWindow()
        return PygameRenderer(window), PygameMenu(window), PygameHumanPlayer(window)

    if ui == "cmd":
        from ui.cmd import CmdHumanPlayer, CmdMenu, CmdRenderer, enable_ansi

        enable_ansi()
        return CmdRenderer(), CmdMenu(), CmdHumanPlayer()

    raise ValueError(f"Unknown local ui: {ui!r} (the web UI uses build_web_app)")


def build_application(config: Optional[GameConfig] = None, ui: str = DEFAULT_UI) -> Application:
    config = config or GameConfig()
    renderer, menu, human = _build_ui(ui)
    # [SWAP] ONE human selector for every player (hot-seat). To mix humans and bots use a
    # mapping instead: {Player.RED: human, Player.BLUE: my_bot, ...}
    selectors = human
    return Application(menu, MatchRunner(new_game, renderer, selectors), config)


def build_web_app(config: Optional[GameConfig] = None):
    """The FastAPI app for the website (the browser is the renderer and the input)."""
    try:
        from ui.web import create_app
    except ImportError as error:
        raise SystemExit(
            "The web interface needs FastAPI and uvicorn:  pip install -r requirements-web.txt"
        ) from error
    return create_app(new_game, config or GameConfig())


def run_web(host: str, port: int, config: Optional[GameConfig] = None) -> None:
    try:
        import uvicorn
    except ImportError as error:
        raise SystemExit("The web interface needs uvicorn:  pip install -r requirements-web.txt") from error
    app = build_web_app(config)
    print(f"Grid Color War: open http://{host}:{port}   (Ctrl+C to stop)")
    print("Rules: " + (", ".join((config or GameConfig()).rules.names) or "none"))
    # One process only: game sessions are kept in memory.
    uvicorn.run(app, host=host, port=port, log_level="warning")


def _split(values: Optional[Sequence[str]]) -> List[str]:
    """['a,b', 'c'] -> ['a', 'b', 'c']"""
    return [name.strip() for value in values or [] for name in value.split(",") if name.strip()]


def _parse_value(text: str):
    if text.lower() in ("true", "false"):
        return text.lower() == "true"
    try:
        return int(text)
    except ValueError:
        return text


def build_ruleset(
    only: Optional[Sequence[str]] = None,
    enable: Optional[Sequence[str]] = None,
    disable: Optional[Sequence[str]] = None,
    settings: Optional[Sequence[str]] = None,
) -> RuleSet:
    """Command-line choices -> RuleSet. Raises ValueError on unknown rules/options."""
    names = _split(only)
    if names:
        rules = RuleSet.none() if names == ["none"] else RuleSet.of(*names)
    else:
        rules = RuleSet.default()
    rules = rules.with_(*_split(enable)).without(*_split(disable))
    for setting in settings or []:
        key, separator, value = setting.partition("=")
        rule_name, dot, option = key.partition(".")
        if not (separator and dot and option):
            raise ValueError(f"--set expects RULE.OPTION=VALUE, got '{setting}'")
        rules = rules.with_options(rule_name, **{option: _parse_value(value)})
    return rules


def format_rules(rules: RuleSet) -> str:
    lines = []
    for rule in rules.describe():
        options = ", ".join(f"{k}={v}" for k, v in rule["options"].items())
        lines.append(f"[{'x' if rule['enabled'] else ' '}] {rule['name']}" + (f"  ({options})" if options else ""))
        lines.append(f"      {rule['description']}")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Grid Color War")
    parser.add_argument("--ui", choices=UI_CHOICES, default=DEFAULT_UI)
    parser.add_argument("--host", default="127.0.0.1", help="web only (0.0.0.0 = reachable from your network)")
    parser.add_argument("--port", type=int, default=8000, help="web only")
    game = parser.add_argument_group("starting values of a game (changeable per game in pygame / web)")
    game.add_argument("--players", type=int, metavar="N", help="number of players, 2 to 6 (default 2)")
    game.add_argument("--board-size", type=int, metavar="N", help="board side (default 5)")
    game.add_argument("--turns", type=int, metavar="N", help="turns shared by all players (default 50)")
    rules = parser.add_argument_group("rules (see --list-rules)")
    rules.add_argument("--list-rules", action="store_true", help="show all rules and which are on, then exit")
    rules.add_argument("--only", action="append", metavar="RULES", help="comma-separated: ONLY these rules are on ('none' = no rule)")
    rules.add_argument("--enable", action="append", metavar="RULES", help="comma-separated rules to turn on")
    rules.add_argument("--disable", action="append", metavar="RULES", help="comma-separated rules to turn off")
    rules.add_argument("--set", action="append", metavar="RULE.OPTION=VALUE", help="change a rule option, e.g. line_streak_wipe.limit=2")
    args = parser.parse_args(argv)

    try:
        ruleset = build_ruleset(args.only, args.enable, args.disable, args.set)
    except ValueError as error:
        parser.error(str(error))
    if args.list_rules:
        print(format_rules(ruleset))
        return
    try:
        config = GameConfig.from_dict(
            {k: v for k, v in {"num_players": args.players, "board_size": args.board_size,
                               "total_turns": args.turns}.items() if v is not None},
            base=GameConfig(rules=ruleset),
        )
    except ValueError as error:
        parser.error(str(error))

    if args.ui == "web":
        run_web(args.host, args.port, config)
    else:
        build_application(config, ui=args.ui).run()


if __name__ == "__main__":
    main()
