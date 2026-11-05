"""Test doubles shared by the test modules."""
import itertools

from core import Card, CardSource, Position
from players import MatchAborted, MoveSelector
from ui import AfterMatchChoice, MainChoice, Menu, Renderer


def card(*offsets, size=3) -> Card:
    return Card(size, frozenset(Position(r, c) for r, c in offsets))


class FixedCardSource(CardSource):
    """Cycles through the given cards, forever."""

    def __init__(self, *cards):
        self._cards = itertools.cycle(cards)

    def next_card(self):
        return next(self._cards)


class ScriptedSelector(MoveSelector):
    """Plays the given (row, col) moves, then aborts the match."""

    def __init__(self, *moves):
        self._moves = iter(moves)

    def choose_move(self, game):
        try:
            return Position(*next(self._moves))
        except StopIteration:
            raise MatchAborted()


class RecordingRenderer(Renderer):
    def __init__(self):
        self.game_renders = 0
        self.game_over_renders = 0

    def render_game(self, game, last_move):
        self.game_renders += 1

    def render_game_over(self, game):
        self.game_over_renders += 1


class ScriptedMenu(Menu):
    def __init__(self, main_choices, after_choices=()):
        self._main = iter(main_choices)
        self._after = iter(after_choices)
        self.goodbyes = 0

    def ask_main_choice(self) -> MainChoice:
        return next(self._main)

    def ask_after_match(self) -> AfterMatchChoice:
        return next(self._after)

    def show_goodbye(self):
        self.goodbyes += 1
