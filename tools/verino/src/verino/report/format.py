"""Human and JSON forms of a check :class:`~verino.rules.Report` (same data, two views)."""

from __future__ import annotations

import json
from typing import Any

from verino.rules import Finding, Report

REPORT_SCHEMA = "verino-report/1"


def _counts(report: Report) -> dict[str, int]:
    active = report.active
    return {
        "errors": sum(f.severity == "error" for f in active),
        "warnings": sum(f.severity == "warning" for f in active),
        "info": sum(f.severity == "info" for f in active),
        "acknowledged": len(report.findings) - len(active),
    }


def summary(report: Report) -> str:
    c = _counts(report)
    return (
        f"{report.file}: {report.status} ({c['errors']} errors, {c['warnings']} warnings, "
        f"{c['info']} info, {c['acknowledged']} acknowledged)"
    )


def to_text(report: Report) -> str:
    """One line per finding, then a summary line."""
    lines = [str(f) for f in report.findings]
    lines.append(summary(report))
    return "\n".join(lines) + "\n"


def _finding(f: Finding) -> dict[str, Any]:
    d = f.diagnostic
    return {
        "id": d.rule_id,
        "severity": d.severity,
        "file": d.loc.file,
        "line": d.loc.line,
        "col": d.loc.col,
        "path": d.path,
        "message": d.message,
        "why": d.why,
        "fix": d.fix,
        "pin": f.pin,
        "device": f.device,
        "acknowledged": f.acknowledged,
        "ack_reason": f.ack_reason,
    }


def to_dict(report: Report) -> dict[str, Any]:
    return {
        "schema": REPORT_SCHEMA,
        "file": report.file,
        "status": report.status,
        "exit_code": report.exit_code,
        "counts": _counts(report),
        "findings": [_finding(f) for f in report.findings],
    }


def to_json(report: Report) -> str:
    return json.dumps(to_dict(report), indent=2, ensure_ascii=False) + "\n"
