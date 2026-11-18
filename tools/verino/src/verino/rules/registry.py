"""Rule registration: one function per rule ID, one module per rule (``rules/<id>.py``)."""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from verino.rules.context import Context, Hit

RuleFunc = Callable[["Context"], Iterable["Hit"]]


@dataclass(frozen=True)
class RegisteredRule:
    rule_id: str
    func: RuleFunc
    needs_chip: bool


_RULES: dict[str, RegisteredRule] = {}

# IDs produced by the loader or the engine itself rather than by a rule module.
BUILTIN_IDS = frozenset({"E-YAML-001", "E-SCHEMA-001", "I-ACK-001"})


def rule(rule_id: str, *, needs_chip: bool = True) -> Callable[[RuleFunc], RuleFunc]:
    """Register ``func`` as the implementation of ``rule_id``."""

    def decorator(func: RuleFunc) -> RuleFunc:
        if rule_id in _RULES or rule_id in BUILTIN_IDS:
            raise ValueError(f"rule {rule_id} is already registered")
        _RULES[rule_id] = RegisteredRule(rule_id, func, needs_chip)
        return func

    return decorator


def registered() -> dict[str, RegisteredRule]:
    """All rules, importing every module in ``verino.rules.checks`` once."""
    package = importlib.import_module("verino.rules.checks")
    for info in pkgutil.iter_modules(package.__path__):
        importlib.import_module(f"{package.__name__}.{info.name}")
    return dict(sorted(_RULES.items()))
