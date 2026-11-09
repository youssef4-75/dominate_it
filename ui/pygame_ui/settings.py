"""The settings screen: choose the players, the parameters and the rules of the NEXT game.

Built from the schema in core (`SETTINGS` and `RuleSet.describe()`), so a new
parameter, rule or rule option shows up here without touching this file.
Immediate-mode: every frame draws the widgets and records the clickable areas.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import pygame

from core import GameConfig, RuleSet, SETTINGS
from ui.pygame_ui.drawing import Button, draw_text, wrap_lines
from ui.pygame_ui.theme import BACKGROUND, BUTTON, BUTTON_HOVER, MUTED, PANEL, TEXT, WARNING, WINDOW_SIZE
from ui.pygame_ui.window import PygameWindow

Hotspot = Tuple[pygame.Rect, Callable[[], None]]

LEFT_X, LEFT_W = 40, 380
RIGHT_X, RIGHT_W = 450, 370
TOP = 116
CHECKED = (90, 200, 120)


class _Form:
    """The values being edited (plain data, no pygame)."""

    def __init__(self, config: GameConfig) -> None:
        self.params: Dict[str, Any] = {}
        self.enabled: Set[str] = set()
        self.options: Dict[str, Dict[str, Any]] = {}
        self.load(config)

    def load(self, config: GameConfig) -> None:
        data = config.to_dict()
        self.params = {k: v for k, v in data.items() if k != "rules"}
        self.enabled = set(data["rules"]["enabled"])
        self.options = {n: dict(v) for n, v in data["rules"]["options"].items()}

    def reset(self) -> None:
        """Back to the default settings of the game."""
        self.load(GameConfig())

    def to_config(self) -> GameConfig:
        data = dict(self.params)
        data["rules"] = {"enabled": sorted(self.enabled), "options": self.options}
        return GameConfig.from_dict(data)


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


class SettingsScreen:
    def __init__(self, window: PygameWindow) -> None:
        self._window = window

    def run(self, current: GameConfig) -> Optional[GameConfig]:
        """Edit the settings; returns the new GameConfig (Start) or None (Back)."""
        form = _Form(current)
        error = ""
        w = self._window
        result: Dict[str, Any] = {}

        def start() -> None:
            nonlocal error
            try:
                result["config"] = form.to_config()
            except ValueError as problem:
                error = str(problem)

        def back() -> None:
            result["config"] = None

        while "config" not in result:
            events = w.pump()
            if w.closed:
                return None
            hotspots, hovered_rule = self._draw(form, error, start, back)
            for event in events:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    back()
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    start()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, action in hotspots:
                        if rect.collidepoint(event.pos):
                            if action is not start:
                                error = ""  # a change clears the previous error message
                            action()
                            break
            w.flip()
        return result["config"]

    # -- drawing + hotspots --------------------------------------------------
    def _draw(
        self, form: _Form, error: str, start: Callable[[], None], back: Callable[[], None]
    ) -> Tuple[List[Hotspot], Optional[str]]:
        w = self._window
        screen, fonts = w.screen, w.fonts
        mouse = pygame.mouse.get_pos()
        hotspots: List[Hotspot] = []
        screen.fill(BACKGROUND)
        draw_text(screen, fonts.title, "GAME SETTINGS", (WINDOW_SIZE[0] // 2, 36), TEXT, "center")

        # ---- left: the game parameters
        draw_text(screen, fonts.small, "GAME", (LEFT_X, 84), MUTED)
        for index, setting in enumerate(SETTINGS):
            rect = pygame.Rect(LEFT_X, TOP + index * 50, LEFT_W, 42)
            pygame.draw.rect(screen, PANEL, rect, border_radius=10)
            draw_text(screen, fonts.small, setting.label, (rect.x + 14, rect.centery), TEXT, "midleft")
            if setting.kind == "bool":
                key = setting.key
                self._checkbox(screen, hotspots, rect.right - 12 - 28, rect.y + 7, bool(form.params[key]),
                               lambda key=key: form.params.__setitem__(key, not form.params[key]))
            else:
                key = setting.key

                def change(delta: int, key=key, setting=setting) -> None:
                    form.params[key] = _clamp(form.params[key] + delta * setting.step, setting.minimum, setting.maximum)

                self._stepper(screen, fonts, hotspots, rect.right - 12 - 144, rect.y + 4,
                              str(form.params[setting.key]), lambda change=change: change(-1), lambda change=change: change(1))

        # ---- right: the rules
        draw_text(screen, fonts.small, "RULES  (hover a rule to read it)", (RIGHT_X, 84), MUTED)
        y = TOP
        hovered_rule: Optional[str] = None
        descriptions: Dict[str, str] = {}
        for rule in RuleSet(frozenset(form.enabled), form.options).describe():
            name, specs = rule["name"], rule["option_specs"]
            descriptions[name] = rule["description"]
            height = 42 + 36 * len(specs)
            rect = pygame.Rect(RIGHT_X, y, RIGHT_W, height)
            on = name in form.enabled
            pygame.draw.rect(screen, PANEL, rect, border_radius=10)
            if rect.collidepoint(mouse):
                hovered_rule = name
            self._checkbox(screen, hotspots, rect.x + 12, rect.y + 7, on,
                           lambda name=name: form.enabled.symmetric_difference_update({name}))
            draw_text(screen, fonts.small, name, (rect.x + 52, rect.y + 21), TEXT if on else MUTED, "midleft")
            for n, spec in enumerate(specs):
                row_y = rect.y + 42 + 36 * n
                draw_text(screen, fonts.small, spec["label"], (rect.x + 52, row_y + 15), MUTED if not on else TEXT, "midleft")
                self._option_control(screen, fonts, hotspots, form, name, spec, rect.right - 12 - 144, row_y, on)
            y += height + 6

        # ---- description of the hovered rule
        box = pygame.Rect(RIGHT_X, 478, RIGHT_W, 112)
        pygame.draw.rect(screen, PANEL, box, border_radius=10)
        text = descriptions.get(hovered_rule or "", "") or "Hover a rule to read what it does."
        for i, line in enumerate(wrap_lines(fonts.small, text, box.width - 24)[:4]):
            draw_text(screen, fonts.small, line, (box.x + 12, box.y + 10 + i * 24), TEXT if hovered_rule else MUTED)

        # ---- errors and buttons
        if error:
            for i, line in enumerate(wrap_lines(fonts.small, error, WINDOW_SIZE[0] - 80)[:2]):
                draw_text(screen, fonts.small, line, (LEFT_X, 598 + i * 22), WARNING)
        buttons = [
            (Button("Back", pygame.Rect(LEFT_X, 632, 150, 52), None), back),
            (Button("Defaults", pygame.Rect(LEFT_X + 170, 632, 170, 52), None), form.reset),
            (Button("Start game", pygame.Rect(WINDOW_SIZE[0] - 40 - 230, 632, 230, 52), None), start),
        ]
        for button, action in buttons:
            button.draw(screen, fonts, button.rect.collidepoint(mouse))
            hotspots.append((button.rect, action))
        return hotspots, hovered_rule

    # -- widgets ---------------------------------------------------------------
    @staticmethod
    def _checkbox(screen, hotspots, x, y, checked, toggle) -> None:
        rect = pygame.Rect(x, y, 28, 28)
        pygame.draw.rect(screen, BUTTON, rect, border_radius=6)
        pygame.draw.rect(screen, MUTED, rect, width=2, border_radius=6)
        if checked:
            pygame.draw.lines(screen, CHECKED, False,
                              [(x + 6, y + 15), (x + 12, y + 21), (x + 23, y + 7)], 4)
        hotspots.append((rect.inflate(8, 8), toggle))

    @staticmethod
    def _stepper(screen, fonts, hotspots, x, y, value_text, minus, plus, enabled=True) -> None:
        for rect, label, action in (
            (pygame.Rect(x, y, 34, 34), "-", minus),
            (pygame.Rect(x + 34 + 8 + 60 + 8, y, 34, 34), "+", plus),
        ):
            pygame.draw.rect(screen, BUTTON if enabled else PANEL, rect, border_radius=8)
            pygame.draw.rect(screen, MUTED, rect, width=1, border_radius=8)
            draw_text(screen, fonts.normal, label, rect.center, TEXT if enabled else MUTED, "center")
            if enabled:
                hotspots.append((rect, action))
        draw_text(screen, fonts.normal, value_text, (x + 34 + 8 + 30, y + 17), TEXT if enabled else MUTED, "center")

    def _option_control(self, screen, fonts, hotspots, form, rule, spec, x, y, enabled) -> None:
        key = spec["key"]
        values = form.options[rule]
        if spec["kind"] == "choice":
            rect = pygame.Rect(x, y, 144, 34)
            pygame.draw.rect(screen, BUTTON_HOVER if enabled else PANEL, rect, border_radius=8)
            pygame.draw.rect(screen, MUTED, rect, width=1, border_radius=8)
            draw_text(screen, fonts.small, str(values[key]), rect.center, TEXT if enabled else MUTED, "center")
            choices = spec["choices"]

            def cycle() -> None:
                if rule in form.enabled:  # checked when clicked: the screen may be a frame behind
                    values[key] = choices[(choices.index(values[key]) + 1) % len(choices)]

            if enabled:
                hotspots.append((rect, cycle))
            return

        def change(delta: int) -> None:
            if rule in form.enabled:  # checked when clicked: the screen may be a frame behind
                values[key] = _clamp(values[key] + delta, spec["min"], spec["max"])

        self._stepper(screen, fonts, hotspots, x, y, str(values[key]),
                      lambda: change(-1), lambda: change(1), enabled)
