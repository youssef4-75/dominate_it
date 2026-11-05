import pytest

from core import Game, GameConfig, Player
from match_runner import MatchRunner, MatchStatus
from tests.helpers import FixedCardSource, RecordingRenderer, ScriptedSelector, card


def factory(total_turns=2):
    return lambda: Game(GameConfig(total_turns=total_turns), FixedCardSource(card((0, 0))))


def test_full_match_renders_every_state_then_game_over():
    renderer = RecordingRenderer()
    runner = MatchRunner(
        factory(2),
        renderer,
        {Player.RED: ScriptedSelector((0, 0)), Player.BLUE: ScriptedSelector((1, 1))},
    )
    assert runner.run() is MatchStatus.FINISHED
    assert renderer.game_renders == 3  # before move 1, before move 2, final
    assert renderer.game_over_renders == 1


def test_abort_stops_the_match_without_game_over():
    renderer = RecordingRenderer()
    runner = MatchRunner(
        factory(10),
        renderer,
        {Player.RED: ScriptedSelector((0, 0)), Player.BLUE: ScriptedSelector()},
    )
    assert runner.run() is MatchStatus.ABORTED
    assert renderer.game_over_renders == 0


def test_every_player_needs_a_selector():
    with pytest.raises(ValueError):
        MatchRunner(factory(), RecordingRenderer(), {Player.RED: ScriptedSelector()})
