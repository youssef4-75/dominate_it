"""GameConfig: per-game settings, players, (de)serialization and the settings schema."""
import pytest

from core import (
    MAX_PLAYERS, MIN_PLAYERS, PALETTE, SETTINGS, GameConfig, Player, RuleSet, players_for,
)
from core.rules import RULES


def test_default_config_is_two_players_red_and_blue():
    config = GameConfig()
    assert config.players == (Player.RED, Player.BLUE)
    assert config.rules == RuleSet.default()


def test_players_for_gives_the_first_colors_of_the_palette_in_order():
    assert [p.name for p in players_for(4)] == ["RED", "BLUE", "GREEN", "YELLOW"]
    assert players_for(MAX_PLAYERS) == PALETTE
    for bad in (0, 1, MAX_PLAYERS + 1):
        with pytest.raises(ValueError, match="between"):
            players_for(bad)


def test_every_player_has_a_distinct_color_and_a_hex_form():
    assert len({p.color for p in PALETTE}) == len(PALETTE) == MAX_PLAYERS == 6
    assert Player.RED.hex_color == "#e24848"
    assert Player.RED == Player("RED", (226, 72, 72)) and hash(Player.RED) == hash(Player("RED", (226, 72, 72)))


def test_invalid_player_lists_are_rejected():
    with pytest.raises(ValueError):
        GameConfig(players=(Player.RED,))
    with pytest.raises(ValueError):
        GameConfig(players=PALETTE + (Player("PINK", (255, 0, 255)),))
    with pytest.raises(ValueError, match="different names"):
        GameConfig(players=(Player.RED, Player("RED", (1, 2, 3))))


def test_other_invalid_values_are_rejected():
    for bad in (dict(board_size=0), dict(card_size=4), dict(colored_cells=10), dict(total_turns=0),
                dict(preview_cards=-1), dict(rules="line_bonus")):
        with pytest.raises(ValueError):
            GameConfig(**bad)


# ---------------------------------------------------------------- dict form
def test_round_trip_through_a_dict():
    custom = GameConfig(
        board_size=7, total_turns=80, colored_cells=5, preview_cards=1, diagonals_count=False,
        players=players_for(5),
        rules=RuleSet.default().without("catch_up_cards").with_options("line_streak_wipe", limit=2),
    )
    assert GameConfig.from_dict(custom.to_dict()) == custom
    assert GameConfig.from_dict(GameConfig().to_dict()) == GameConfig()


def test_a_partial_dict_keeps_the_rest_of_the_base_config():
    base = GameConfig(total_turns=33, board_size=6)
    config = GameConfig.from_dict({"num_players": 3}, base=base)
    assert len(config.players) == 3 and config.total_turns == 33 and config.board_size == 6
    assert GameConfig.from_dict({}) == GameConfig()


def test_the_rules_in_a_dict_replace_the_whole_rule_set():
    config = GameConfig.from_dict({"rules": {"enabled": ["line_bonus"]}})
    assert config.rules.names == ("line_bonus",)


@pytest.mark.parametrize("bad, message", [
    ({"nope": 1}, "Unknown setting"),
    ({"board_size": "5"}, "whole number"),
    ({"board_size": True}, "whole number"),
    ({"board_size": 5.5}, "whole number"),
    ({"diagonals_count": 1}, "true or false"),
    ({"num_players": 9}, "between"),
    ({"num_players": "3"}, "whole number"),
    ({"total_turns": 0}, "total_turns"),
    ({"rules": {"enabled": ["nope"]}}, "Unknown rule"),
    ({"rules": {"enabled": "line_bonus"}}, "list of rule names"),
    ({"rules": {"options": {"line_streak_wipe": {"limit": 0}}}}, ">= 1"),
    ({"rules": {"options": {"full_board_win": {"winner": "nobody"}}}}, "one of"),
    ({"rules": {"extra": 1}}, "Unknown key"),
    ("not a dict", "object"),
])
def test_bad_dicts_give_a_readable_error(bad, message):
    with pytest.raises(ValueError, match=message):
        GameConfig.from_dict(bad)


# ---------------------------------------------------------------- schema used by the settings screens
def test_every_value_offered_by_the_settings_screens_is_accepted_by_the_core():
    for setting in SETTINGS:
        if setting.kind == "bool":
            for value in (True, False):
                GameConfig.from_dict({setting.key: value})
        else:
            for value in (setting.minimum, setting.maximum):
                GameConfig.from_dict({setting.key: value})  # a screen may be narrower than the core
        assert setting.key in GameConfig().to_dict()


def test_every_rule_option_range_is_accepted_by_the_core():
    for rule in RULES:
        for key, spec in rule.options_spec.items():
            values = list(spec.choices) if spec.choices else [spec.minimum, spec.maximum, spec.default]
            for value in values:
                rule(**{key: value})  # does not raise
            assert spec.default in values or spec.choices
