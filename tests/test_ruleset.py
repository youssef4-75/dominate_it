"""RuleSet: the on/off switches of the rules."""
import pytest

from core import GameConfig, LineBonus, RuleSet
from core.rules import RULES

ALL = tuple(rule.name for rule in RULES)


def test_default_rules_and_their_execution_order():
    assert RuleSet.default().names == (
        "full_board_win", "line_streak_wipe", "line_bonus", "catch_up_cards",
    )
    assert "full_board_flip" not in RuleSet.default().names  # off by default


def test_none_and_of():
    assert RuleSet.none().names == ()
    assert RuleSet.of("line_bonus").names == ("line_bonus",)


def test_names_are_always_in_execution_order_whatever_the_order_given():
    assert RuleSet.of("catch_up_cards", "line_bonus", "full_board_win").names == (
        "full_board_win", "line_bonus", "catch_up_cards",
    )


def test_with_and_without_return_new_rulesets():
    base = RuleSet.default()
    changed = base.without("catch_up_cards").with_("full_board_flip")
    assert not changed.is_enabled("catch_up_cards") and changed.is_enabled("full_board_flip")
    assert base.is_enabled("catch_up_cards")  # the original is untouched


def test_unknown_rule_names_are_rejected_everywhere():
    for call in (
        lambda: RuleSet.of("nope"),
        lambda: RuleSet.default().with_("nope"),
        lambda: RuleSet.default().without("nope"),
        lambda: RuleSet.default().is_enabled("nope"),
        lambda: RuleSet.default().with_options("nope", x=1),
    ):
        with pytest.raises(ValueError, match="Unknown rule 'nope'"):
            call()


def test_options_have_defaults_can_be_changed_and_are_validated():
    rules = RuleSet.default()
    assert rules.option("line_streak_wipe", "limit") == 3
    assert rules.option("catch_up_cards", "gap") == 10
    tuned = rules.with_options("line_streak_wipe", limit=2)
    assert tuned.option("line_streak_wipe", "limit") == 2
    assert rules.option("line_streak_wipe", "limit") == 3
    with pytest.raises(ValueError, match="no option"):
        rules.with_options("line_streak_wipe", gap=2)


def test_build_gives_fresh_rule_objects_with_the_options():
    rules = RuleSet.of("line_bonus", "line_streak_wipe").with_options("line_streak_wipe", limit=5)
    first, second = rules.build(), rules.build()
    assert [type(r).__name__ for r in first] == ["LineStreakWipe", "LineBonus"]
    assert first[0].option("limit") == 5
    assert first[1] is not second[1] and isinstance(first[1], LineBonus)


def test_describe_lists_every_rule():
    rows = RuleSet.default().describe()
    assert [row["name"] for row in rows] == list(ALL)
    wipe = next(row for row in rows if row["name"] == "line_streak_wipe")
    assert wipe["enabled"] and wipe["options"] == {"limit": 3} and wipe["description"]


def test_every_rule_has_a_name_and_a_description():
    assert len(set(ALL)) == len(ALL)
    assert all(rule.description for rule in RULES)


def test_game_config_uses_the_default_rules_and_validates_the_type():
    assert GameConfig().rules == RuleSet.default()
    assert GameConfig(rules=RuleSet.none()).rules.names == ()
    with pytest.raises(ValueError):
        GameConfig(rules="line_bonus")


# ---------------------------------------------------------------- dict form and option checks
def test_round_trip_through_a_dict_and_equality_is_about_behavior():
    tuned = RuleSet.default().without("line_bonus").with_options("catch_up_cards", gap=4)
    assert RuleSet.from_dict(tuned.to_dict()) == tuned
    assert RuleSet.from_dict(RuleSet.default().to_dict()) == RuleSet.default()
    # an explicit default and an absent option behave the same, so they are equal
    assert RuleSet.default().with_options("catch_up_cards", gap=10) == RuleSet.default()
    assert RuleSet.default().with_options("catch_up_cards", gap=11) != RuleSet.default()


def test_option_values_are_checked_when_the_ruleset_is_created():
    with pytest.raises(ValueError, match=">= 1"):
        RuleSet.default().with_options("line_streak_wipe", limit=0)
    with pytest.raises(ValueError, match="whole number"):
        RuleSet.default().with_options("line_streak_wipe", limit="3")
    with pytest.raises(ValueError, match="whole number"):
        RuleSet.default().with_options("catch_up_cards", gap=True)
    with pytest.raises(ValueError, match="one of"):
        RuleSet.default().with_options("full_board_win", winner="nobody")


def test_describe_gives_what_a_settings_screen_needs_for_each_option():
    rows = {row["name"]: row for row in RuleSet.default().describe()}
    wipe = rows["line_streak_wipe"]["option_specs"][0]
    assert wipe == {"key": "limit", "label": "Lines in a row", "kind": "int", "value": 3,
                    "default": 3, "min": 1, "max": 20, "choices": None}
    win = rows["full_board_win"]["option_specs"][0]
    assert win["kind"] == "choice" and win["choices"] == ["most_cells", "mover"] and win["value"] == "most_cells"
    assert rows["line_bonus"]["option_specs"] == []
