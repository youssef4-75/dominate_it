from application import Application
from match_runner import MatchStatus
from tests.helpers import ScriptedMenu
from ui import AfterMatchChoice, MainChoice


class FakeRunner:
    def __init__(self, *statuses):
        self._statuses = iter(statuses)
        self.runs = 0

    def run(self):
        self.runs += 1
        return next(self._statuses)


def test_quit_right_away():
    menu = ScriptedMenu([MainChoice.QUIT])
    runner = FakeRunner()
    Application(menu, runner).run()
    assert runner.runs == 0 and menu.goodbyes == 1


def test_replay_then_home_then_quit():
    menu = ScriptedMenu(
        [MainChoice.PLAY, MainChoice.QUIT],
        [AfterMatchChoice.REPLAY, AfterMatchChoice.HOME],
    )
    runner = FakeRunner(MatchStatus.FINISHED, MatchStatus.FINISHED)
    Application(menu, runner).run()
    assert runner.runs == 2 and menu.goodbyes == 1


def test_aborted_match_goes_back_home_without_asking():
    menu = ScriptedMenu([MainChoice.PLAY, MainChoice.QUIT])
    runner = FakeRunner(MatchStatus.ABORTED)
    Application(menu, runner).run()
    assert runner.runs == 1
