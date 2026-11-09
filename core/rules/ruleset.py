"""RuleSet: which rules are ON, with which options. The "checkboxes" of the game."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Iterable, List, Mapping, Tuple

from core.rules.base import Rule
from core.rules.registry import BY_NAME, RULES


def _check_name(name: str) -> None:
    if name not in BY_NAME:
        raise ValueError(f"Unknown rule '{name}'. Available: {', '.join(BY_NAME)}")


@dataclass(frozen=True, eq=False)
class RuleSet:
    """Immutable. Every change returns a new RuleSet:

        RuleSet.default().without("catch_up_cards").with_("full_board_flip")
        RuleSet.of("line_bonus")                       # only this rule
        RuleSet.none()                                 # plain game, no special rules
        RuleSet.default().with_options("line_streak_wipe", limit=2)
    """

    enabled: FrozenSet[str] = field(default_factory=frozenset)
    options: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "enabled", frozenset(self.enabled))
        for name in self.enabled:
            _check_name(name)
        for name, values in self.options.items():
            _check_name(name)
            BY_NAME[name](**values)  # raises ValueError for unknown options or invalid values

    def __eq__(self, other: object) -> bool:
        """Two RuleSets are equal when they behave the same (effective options)."""
        return isinstance(other, RuleSet) and self.to_dict() == other.to_dict()

    def __hash__(self) -> int:
        return hash(self.names)

    # -- constructors -------------------------------------------------------
    @classmethod
    def default(cls) -> "RuleSet":
        return cls(frozenset(rule.name for rule in RULES if rule.enabled_by_default))

    @classmethod
    def none(cls) -> "RuleSet":
        return cls(frozenset())

    @classmethod
    def of(cls, *names: str) -> "RuleSet":
        return cls(frozenset(names))

    # -- changes (return a new RuleSet) ------------------------------------
    def with_(self, *names: str) -> "RuleSet":
        return RuleSet(self.enabled | frozenset(names), self.options)

    def without(self, *names: str) -> "RuleSet":
        for name in names:
            _check_name(name)
        return RuleSet(self.enabled - frozenset(names), self.options)

    def with_options(self, name: str, **values: Any) -> "RuleSet":
        _check_name(name)
        merged: Dict[str, Mapping[str, Any]] = dict(self.options)
        merged[name] = {**self.options.get(name, {}), **values}
        return RuleSet(self.enabled, merged)

    # -- queries ------------------------------------------------------------
    def is_enabled(self, name: str) -> bool:
        _check_name(name)
        return name in self.enabled

    @property
    def names(self) -> Tuple[str, ...]:
        """Enabled rules, in execution order."""
        return tuple(rule.name for rule in RULES if rule.name in self.enabled)

    def option(self, name: str, key: str) -> Any:
        """The effective value of an option (the default if not changed)."""
        _check_name(name)
        return {**BY_NAME[name].option_defaults(), **self.options.get(name, {})}[key]

    def build(self) -> List[Rule]:
        """Fresh rule objects (rules may keep per-game state), in execution order."""
        return [BY_NAME[name](**self.options.get(name, {})) for name in self.names]

    def describe(self) -> List[Dict[str, Any]]:
        """All rules with their state and option specs, for display (--list-rules, settings screens)."""
        rows = []
        for rule in RULES:
            specs = []
            for key, spec in rule.options_spec.items():
                specs.append({
                    "key": key, "label": spec.label or key, "kind": spec.kind,
                    "value": self.option(rule.name, key), "default": spec.default,
                    "min": spec.minimum, "max": spec.maximum,
                    "choices": list(spec.choices) if spec.choices else None,
                })
            rows.append({
                "name": rule.name,
                "enabled": rule.name in self.enabled,
                "description": rule.description,
                "options": {spec["key"]: spec["value"] for spec in specs},
                "option_specs": specs,
            })
        return rows

    # -- (de)serialization: JSON-friendly, used by the web API and the settings screens ---
    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": list(self.names),
            "options": {
                rule.name: {key: self.option(rule.name, key) for key in rule.options_spec}
                for rule in RULES if rule.options_spec
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RuleSet":
        """Inverse of to_dict. Raises ValueError on anything unexpected."""
        if not isinstance(data, Mapping):
            raise ValueError("rules must be an object like {\"enabled\": [...], \"options\": {...}}")
        unknown = set(data) - {"enabled", "options"}
        if unknown:
            raise ValueError(f"Unknown key(s) in rules: {sorted(unknown)}")
        enabled = data.get("enabled", [])
        if isinstance(enabled, (str, bytes)) or not all(isinstance(n, str) for n in enabled):
            raise ValueError("rules.enabled must be a list of rule names")
        options = data.get("options", {})
        if not isinstance(options, Mapping) or not all(isinstance(v, Mapping) for v in options.values()):
            raise ValueError("rules.options must be an object of objects")
        return cls(frozenset(enabled), {name: dict(values) for name, values in options.items()})
