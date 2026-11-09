import pytest

from core import Game, GameConfig, Player, RuleSet, players_for
from match_runner import MatchRunner, MatchStatus
from tests.helpers import FixedCardSource, RecordingRenderer, ScriptedSelector, card


def factory(config):
    return Game(config, FixedCardSource(card((0, 0))))


def config(turns=2, players=2):
    return GameConfig(total_turns=turns, players=players_for(players), rules=RuleSet.none())


def test_full_match_renders_every_state_then_game_over():
    renderer = RecordingRenderer()
    runner = MatchRunner(
        factory,
        renderer,
        {Player.RED: ScriptedSelector((0, 0)), Player.BLUE: ScriptedSelector((1, 1))},
    )
    assert runner.run(config(2)) is MatchStatus.FINISHED
    assert renderer.game_renders == 3  # before move 1, before move 2, final
    assert renderer.game_over_renders == 1


def test_abort_stops_the_match_without_game_over():
    renderer = RecordingRenderer()
    runner = MatchRunner(
        factory,
        renderer,
        {Player.RED: ScriptedSelector((0, 0)), Player.BLUE: ScriptedSelector()},
    )
    assert runner.run(config(10)) is MatchStatus.ABORTED
    assert renderer.game_over_renders == 0


def test_every_player_of_the_game_needs_a_selector():
    runner = MatchRunner(factory, RecordingRenderer(), {Player.RED: ScriptedSelector()})
    with pytest.raises(ValueError, match="BLUE"):
        runner.run(config())


def test_one_selector_can_serve_every_player_whatever_their_number():
    renderer = RecordingRenderer()
    shared = ScriptedSelector((0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (0, 1))
    runner = MatchRunner(factory, renderer, shared)
    assert runner.run(config(turns=6, players=3)) is MatchStatus.FINISHED
    assert renderer.game_renders == 7 and renderer.game_over_renders == 1


def test_a_mapping_must_cover_all_the_players_of_a_three_player_game():
    two_only = {Player.RED: ScriptedSelector(), Player.BLUE: ScriptedSelector()}
    runner = MatchRunner(factory, RecordingRenderer(), two_only)
    with pytest.raises(ValueError, match="GREEN"):
        runner.run(config(players=3))


def test_each_match_gets_its_own_settings():
    seen = []
    runner = MatchRunner(
        lambda cfg: seen.append(cfg) or factory(cfg), RecordingRenderer(), ScriptedSelector()
    )
    runner.run(config(turns=5, players=3))
    runner.run(config(turns=9, players=2))
    assert [(c.total_turns, len(c.players)) for c in seen] == [(5, 3), (9, 2)]
