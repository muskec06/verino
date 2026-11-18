"""``verino pins check --write``: fill the tool-owned ``reserved`` and ``validation`` blocks.

Only those two top-level blocks are replaced; every user field, comment and key order is
kept by the round-trip YAML writer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from verino import __version__
from verino.chipdata.db import ChipData, ChipDB, ModuleData
from verino.model import load_hardware, set_tool_block
from verino.model.checksum import content_checksum
from verino.model.yamlio import dump_text
from verino.rules import Report, check

STALE_VALIDATION = "W-VAL-001"

# Chip pin groups that are never available to the user, with their ``why`` label.
_GROUPS = (("spi_flash_pins", "flash"), ("usb_pins", "usb"), ("uart0_pins", "uart0_console"))


def _num(pin: str) -> int:
    return int(pin.removeprefix("GPIO"))


def reserved_pins(chip: ChipData, module: ModuleData) -> list[tuple[list[str], str]]:
    """``(pins, why)`` pairs, ordered by lowest GPIO number."""
    by_why: dict[str, set[str]] = {}
    for key, why in _GROUPS:
        for pin in chip.pins.values():
            if key in pin.groups:
                by_why.setdefault(why, set()).add(pin.name)
    for pin_name, use in module.internal.items():
        by_why.setdefault(use, set()).add(pin_name)
    octal = [p.name for p in chip.pins.values() if "octal_spi_pins" in p.groups]
    if module.psram_interface == "octal":
        by_why.setdefault("octal_psram", set()).update(octal)
    elif module.flash_interface == "octal":
        by_why.setdefault("octal_flash", set()).update(octal)
    pairs = [(sorted(pins, key=_num), why) for why, pins in by_why.items()]
    return sorted(pairs, key=lambda p: (_num(p[0][0]), p[1]))


def pin_range(pins: list[str]) -> str | None:
    """``GPIOa-GPIOb`` for three or more consecutive pins, else ``None``."""
    nums = [_num(p) for p in pins]
    if len(nums) > 2 and nums == list(range(nums[0], nums[-1] + 1)):
        return f"{pins[0]}-{pins[-1]}"
    return None


def _pins_value(pins: list[str]) -> str | CommentedSeq:
    span = pin_range(pins)
    if span is not None:
        return span
    seq = CommentedSeq(pins)
    seq.fa.set_flow_style()
    return seq


def _reserved_block(chip: ChipData, module: ModuleData) -> CommentedSeq:
    block = CommentedSeq()
    for pins, why in reserved_pins(chip, module):
        entry = CommentedMap([("pins", _pins_value(pins)), ("why", why)])
        entry.fa.set_flow_style()
        block.append(entry)
    return block


def _validation_block(report: Report, chip: ChipData, db: ChipDB, checksum: str) -> CommentedMap:
    active = [f for f in report.active if f.rule_id != STALE_VALIDATION]
    severities = {f.severity for f in active}
    status = "error" if "error" in severities else "warnings" if "warning" in severities else "ok"
    ids = CommentedSeq(sorted({f.rule_id for f in active if f.severity != "info"}))
    ids.fa.set_flow_style()
    block = CommentedMap()
    block["tool"] = f"verino {__version__}"
    block["chipdata"] = f"{chip.chip}@{db.version()}"
    block["status"] = status
    block["warnings"] = ids
    block["checksum"] = checksum
    return block


@dataclass(frozen=True)
class WriteResult:
    report: Report
    written: bool
    reason: str = ""


def write_back(path: Path, db: ChipDB | None = None) -> WriteResult:
    """Check ``path``, write ``reserved`` and ``validation`` into it, and check it again."""
    db = db if db is not None else ChipDB()
    result = load_hardware(path)
    report = check(result, db)
    if result.spec is None:
        return WriteResult(report, False, "the file has YAML or schema errors")
    module = db.module(result.spec.module)
    chip = db.chip(module.chip) if module is not None else None
    if module is None or chip is None:
        return WriteResult(report, False, "no chip data for the module")

    doc = result.document
    set_tool_block(doc, "reserved", _reserved_block(chip, module))
    set_tool_block(doc, "validation", _validation_block(report, chip, db, content_checksum(doc)))
    path.write_text(dump_text(doc), encoding="utf-8", newline="\n")
    return WriteResult(check(load_hardware(path), db), True)
