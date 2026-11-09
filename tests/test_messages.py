from core import MoveResult, Player, Position, RuleEvent
from ui.messages import describe_move


def result(*events, **kw):
    base = dict(player=Player.RED, position=Position(0, 0), changed_cells=(),
                new_lines=(), bonus_turn=False, events=tuple(events))
    base.update(kw)
    return MoveResult(**base)


def test_the_move_comes_first_then_one_indented_line_per_event_line():
    text = describe_move(result(RuleEvent("line_bonus", "Full line completed: row 1!\n{player} plays again!")))
    assert text.splitlines() == [
        "RED played at row 1, col 1 (0 cell(s) changed).",
        "  Full line completed: row 1!",
        "  RED plays again!",
    ]


def test_placeholders_are_filled_with_the_formatted_names():
    event = RuleEvent("board_flipped", "{player} -> {next}")
    r = result(event, next_player=Player.GREEN)  # three players: the next one is GREEN
    assert "  RED -> GREEN" in describe_move(r)
    assert "  <RED> -> <GREEN>" in describe_move(r, fmt=lambda p: f"<{p.name}>")


def test_no_events_means_only_the_move_line():
    assert describe_move(result()).count("\n") == 0


def test_has_event():
    r = result(RuleEvent("cells_wiped", "x"))
    assert r.has_event("cells_wiped") and not r.has_event("board_flipped")


def played(count, cells):
    """A game with `count` players where each move paints ONE cell, then it is over."""
    from core import Game, GameConfig, RuleSet, players_for
    from tests.helpers import FixedCardSource, card

    config = GameConfig(players=players_for(count), total_turns=len(cells),
                        rules=RuleSet.none(), preview_cards=0)
    game = Game(config, FixedCardSource(card((0, 0))))
    for row, col in cells:
        game.play(Position(row, col))
    return game


def test_outcome_wording_one_winner_partial_tie_and_full_draw():
    from ui.messages import describe_outcome

    assert describe_outcome(played(2, [(0, 0), (4, 4), (2, 2)])) == "RED wins!"
    assert describe_outcome(played(3, [(0, 0), (1, 1)])) == "RED and BLUE tie for the win!"
    assert describe_outcome(played(3, [(0, 0), (1, 1), (2, 2)])) == "It's a draw!"
    assert describe_outcome(played(2, [(0, 0), (4, 4)])) == "It's a draw!"
    assert describe_outcome(played(2, [(0, 0), (4, 4), (2, 2)]), fmt=lambda p: p.name.lower()) == "red wins!"
