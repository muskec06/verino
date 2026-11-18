"""Output and write-back for ``verino pins solve``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ruamel.yaml.comments import CommentedMap

from verino.chipdata.db import ChipDB
from verino.model import LoadResult, load_hardware
from verino.model.yamlio import dump_text
from verino.report import summary, to_dict
from verino.solve.solver import SolveResult, solve

SOLVE_SCHEMA = "verino-solve/1"


def to_text(result: SolveResult) -> str:
    lines: list[str] = []
    width = max((len(a.slot.path) for a in result.assignments), default=0)
    for a in result.assignments:
        lines.append(f"{a.slot.path.ljust(width)}  {a.pin:<6}  {'; '.join(a.reasons)}")
    lines += list(result.messages)
    if result.status == "solved":
        count = len(result.assignments)
        lines.append(f"{result.file}: solved {count} pin{'' if count == 1 else 's'}")
    elif result.status == "nothing_to_do":
        lines.append(f"{result.file}: no auto pins to solve")
    else:
        lines.append(f"{result.file}: {result.status}")
    if result.report is not None:
        lines.append("check after solving: " + summary(result.report))
    return "\n".join(lines) + "\n"


def to_dict_result(result: SolveResult) -> dict[str, Any]:
    return {
        "schema": SOLVE_SCHEMA,
        "file": result.file,
        "status": result.status,
        "exit_code": result.exit_code,
        "assignments": [
            {
                "path": a.slot.path,
                "owner": a.slot.owner_id,
                "owner_kind": a.slot.owner_kind,
                "role": a.slot.role,
                "pin": a.pin,
                "score": a.score,
                "reasons": list(a.reasons),
            }
            for a in result.assignments
        ],
        "messages": list(result.messages),
        "report": to_dict(result.report) if result.report is not None else None,
    }


def to_json(result: SolveResult) -> str:
    return json.dumps(to_dict_result(result), indent=2, ensure_ascii=False) + "\n"


def solve_file(
    path: Path, db: ChipDB | None = None, *, write: bool = False, reassign: bool = False
) -> SolveResult:
    """Solve ``path``; with ``write`` put the chosen pins into the file as ``origin: solver``."""
    base = load_hardware(path)
    result = solve(base, db, reassign=reassign)
    if write and result.status == "solved":
        path.write_text(solved_text(base, result), encoding="utf-8", newline="\n")
    return result


def solved_text(base: LoadResult, result: SolveResult) -> str:
    """``base`` as YAML text with the chosen pins written as ``origin: solver``.

    Comments, key order and every other field are kept (round-trip). ``base.document``
    is modified in place.
    """
    doc = base.document
    for a in result.assignments:
        section = "buses" if a.slot.owner_kind == "bus" else "devices"
        value = CommentedMap([("pin", a.pin), ("origin", "solver")])
        value.fa.set_flow_style()
        doc[section][a.slot.owner_id][a.slot.role] = value
    return dump_text(doc)
