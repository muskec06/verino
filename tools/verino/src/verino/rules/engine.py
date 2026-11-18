"""Run all rules on a loaded ``hardware.yaml`` and apply acknowledgements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from verino.chipdata.db import ChipDB
from verino.model.diagnostics import Diagnostic
from verino.model.loader import LoadResult
from verino.model.schema import format_path
from verino.rules.context import Context, Hit
from verino.rules.registry import registered

ACK_UNUSED = "I-ACK-001"
Status = Literal["ok", "warnings", "error"]


@dataclass(frozen=True)
class Finding:
    diagnostic: Diagnostic
    pin: str | None = None
    device: str | None = None
    acknowledged: bool = False
    ack_reason: str | None = None

    @property
    def rule_id(self) -> str:
        return self.diagnostic.rule_id

    @property
    def severity(self) -> str:
        return self.diagnostic.severity

    def __str__(self) -> str:
        text = str(self.diagnostic)
        if self.acknowledged:
            text += f" [acknowledged: {self.ack_reason}]"
        return text


@dataclass(frozen=True)
class Report:
    file: str
    findings: tuple[Finding, ...]

    @property
    def active(self) -> tuple[Finding, ...]:
        """Findings that are not acknowledged."""
        return tuple(f for f in self.findings if not f.acknowledged)

    @property
    def status(self) -> Status:
        severities = {f.severity for f in self.active}
        if "error" in severities:
            return "error"
        if "warning" in severities:
            return "warnings"
        return "ok"

    @property
    def exit_code(self) -> int:
        return {"ok": 0, "warnings": 1, "error": 2}[self.status]

    def ids(self, *, include_acknowledged: bool = True) -> list[str]:
        source = self.findings if include_acknowledged else self.active
        return [f.rule_id for f in source]


def _finding(rule_id: str, hit: Hit) -> Finding:
    diag = Diagnostic(rule_id, hit.loc, hit.path, hit.message, hit.why, hit.fix)
    return Finding(diag, hit.pin, hit.device)


def check(result: LoadResult, db: ChipDB | None = None) -> Report:
    """Run every registered rule. Loader errors are returned as they are."""
    if result.spec is None:
        return Report(result.file, tuple(Finding(d) for d in result.diagnostics))
    db = db if db is not None else ChipDB()
    spec = result.spec
    module = db.module(spec.module)
    chip = db.chip(module.chip) if module is not None else None
    ctx = Context(spec, result.document, result.file, db, module, chip)

    findings: list[Finding] = []
    for rule_id, entry in registered().items():
        if entry.needs_chip and chip is None:
            continue
        findings.extend(_finding(rule_id, hit) for hit in entry.func(ctx))

    findings = _apply_acks(ctx, findings)
    findings.sort(key=lambda f: (f.diagnostic.sort_key(), f.pin or "", f.device or ""))
    return Report(result.file, tuple(findings))


def _apply_acks(ctx: Context, findings: list[Finding]) -> list[Finding]:
    used: set[int] = set()
    out: list[Finding] = []
    for finding in findings:
        for index, ack in enumerate(ctx.spec.ack):
            if (
                ack.rule == finding.rule_id
                and (ack.pin is None or ack.pin == finding.pin)
                and (ack.device is None or ack.device == finding.device)
            ):
                used.add(index)
                finding = Finding(finding.diagnostic, finding.pin, finding.device, True, ack.reason)
                break
        out.append(finding)
    for index, ack in enumerate(ctx.spec.ack):
        if index not in used:
            target = " ".join(p for p in (ack.pin, ack.device) if p) or "this file"
            hit = Hit(
                ack.loc,
                format_path(["ack", index]),
                f"acknowledgement of {ack.rule} for {target} matches no finding",
                "A stale acknowledgement hides nothing today but may hide a real problem later.",
                "remove it, or correct the rule ID, pin or device.",
            )
            out.append(_finding(ACK_UNUSED, hit))
    return out
