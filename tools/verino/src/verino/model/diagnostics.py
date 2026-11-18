"""Diagnostics produced while reading ``hardware.yaml``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from verino.model.types import Location

Severity = Literal["error", "warning", "info"]

# Rule IDs used by the loader. Registered in chipdata/rules/rules.yaml in T4.
YAML_ERROR = "E-YAML-001"
SCHEMA_ERROR = "E-SCHEMA-001"


@dataclass(frozen=True)
class Diagnostic:
    """One finding: where, what is wrong, why it matters and how to fix it."""

    rule_id: str
    loc: Location
    path: str
    message: str
    why: str = ""
    fix: str = ""

    @property
    def severity(self) -> Severity:
        if self.rule_id.startswith("E-"):
            return "error"
        if self.rule_id.startswith("W-"):
            return "warning"
        return "info"

    def sort_key(self) -> tuple[str, int, int, str, str]:
        return (self.loc.file, self.loc.line, self.loc.col, self.rule_id, self.message)

    def __str__(self) -> str:
        text = f"{self.rule_id} {self.loc} {self.path}: {self.message}."
        if self.why:
            text += f" {self.why}"
        if self.fix:
            text += f" Fix: {self.fix}"
        return text
