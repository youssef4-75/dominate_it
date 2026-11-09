from application import Application
from core import GameConfig, players_for
from match_runner import MatchStatus
from tests.helpers import ScriptedMenu
from ui import AfterMatchChoice, MainChoice


class FakeRunner:
    def __init__(self, *statuses):
        self._statuses = iter(statuses)
        self.configs = []  # the settings of every match played

    @property
    def runs(self):
        return len(self.configs)

    def run(self, config):
        self.configs.append(config)
        return next(self._statuses)


def test_quit_right_away():
    menu = ScriptedMenu([MainChoice.QUIT])
    runner = FakeRunner()
    Application(menu, runner).run()
    assert runner.runs == 0 and menu.goodbyes == 1


def test_replay_then_home_then_quit_replays_with_the_same_settings():
    menu = ScriptedMenu(
        [MainChoice.PLAY, MainChoice.QUIT],
        [AfterMatchChoice.REPLAY, AfterMatchChoice.HOME],
    )
    runner = FakeRunner(MatchStatus.FINISHED, MatchStatus.FINISHED)
    Application(menu, runner).run()
    assert runner.runs == 2 and menu.goodbyes == 1
    assert runner.configs[0] == runner.configs[1]


def test_aborted_match_goes_back_home_without_asking():
    menu = ScriptedMenu([MainChoice.PLAY, MainChoice.QUIT])
    runner = FakeRunner(MatchStatus.ABORTED)
    Application(menu, runner).run()
    assert runner.runs == 1


def test_each_game_gets_the_settings_chosen_for_it():
    three = GameConfig(players=players_for(3), total_turns=12)
    menu = ScriptedMenu(
        [MainChoice.PLAY, MainChoice.PLAY, MainChoice.QUIT],
        [AfterMatchChoice.HOME, AfterMatchChoice.HOME],
        configs=[three, GameConfig(total_turns=30)],
    )
    runner = FakeRunner(MatchStatus.FINISHED, MatchStatus.FINISHED)
    Application(menu, runner).run()
    assert [c.total_turns for c in runner.configs] == [12, 30]
    assert len(runner.configs[0].players) == 3 and len(runner.configs[1].players) == 2


def test_the_next_game_starts_from_the_previous_settings():
    three = GameConfig(players=players_for(3))
    menu = ScriptedMenu(
        [MainChoice.PLAY, MainChoice.PLAY, MainChoice.QUIT],
        [AfterMatchChoice.HOME, AfterMatchChoice.HOME],
        configs=[three],
    )
    Application(menu, FakeRunner(MatchStatus.FINISHED, MatchStatus.FINISHED)).run()
    assert menu.proposed[0] == GameConfig() and menu.proposed[1] == three


def test_going_back_from_the_settings_plays_nothing():
    menu = ScriptedMenu([MainChoice.PLAY, MainChoice.QUIT], configs=[None])
    runner = FakeRunner()
    Application(menu, runner).run()
    assert runner.runs == 0 and menu.goodbyes == 1


def test_the_application_proposes_the_config_it_was_given():
    start = GameConfig(total_turns=7)
    menu = ScriptedMenu([MainChoice.PLAY, MainChoice.QUIT], [AfterMatchChoice.HOME])
    Application(menu, FakeRunner(MatchStatus.FINISHED), start).run()
    assert menu.proposed[0] == start
