"""The rule catalog ``chipdata/rules/rules.yaml``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from verino.chipdata.db import default_root
from verino.model.yamlio import load_text


@dataclass(frozen=True)
class RuleInfo:
    rule_id: str
    severity: str
    name: str
    summary: str
    level: int
    phase: str
    facts: tuple[str, ...]


def load_catalog(root: Path | None = None) -> dict[str, RuleInfo]:
    root = root if root is not None else default_root()
    doc = load_text((root / "rules" / "rules.yaml").read_text(encoding="utf-8"))
    return {
        str(rule_id): RuleInfo(
            rule_id=str(rule_id),
            severity=str(entry["severity"]),
            name=str(entry["name"]),
            summary=str(entry["summary"]),
            level=int(entry["level"]),
            phase=str(entry["phase"]),
            facts=tuple(str(f) for f in entry.get("facts") or []),
        )
        for rule_id, entry in doc["rules"].items()
    }
