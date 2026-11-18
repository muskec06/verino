"""Pin assignment by backtracking + scoring (``verino pins solve``).

The solver never re-implements a rule. For every open slot it tries each GPIO of the chip
and runs the real rule set on the file with that one pin filled in:

- a candidate that produces an error on the slot is infeasible;
- warnings and infos on the slot lower its score (and are reported as reasons);
- preferences (SPI IO_MUX pins, RTC pins with deep sleep) raise it.

Slots are then filled most-constrained first, candidates best-first, with branch-and-bound
over the total score. Every complete assignment is checked once more as a whole; the best
one without errors wins. Ties are broken by GPIO number, so results are deterministic.
"""

from __future__ import annotations

import dataclasses
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal

from verino.chipdata.db import ChipData, ChipDB
from verino.model.loader import LoadResult
from verino.model.types import AUTO, Bus, Device, HardwareSpec, PinAssignment
from verino.rules import Report, check

# Score weights (policy, not hardware facts; see docs/cli.md).
WARNING_PENALTY = 100
INFO_PENALTY = 10
IOMUX_BONUS = 50
RTC_BONUS = 20
SPECIAL_PIN_PENALTY = 30  # strapping or shared-function pin, avoided while others are free
MAX_LEAVES = 200

SOLVE_ID = "E-PIN-005"
# Bus roles that map to SPI IO_MUX signals; device chip-selects use "cs".
_SPI_SIGNALS = {"sclk": "clk", "mosi": "mosi", "miso": "miso"}

Status = Literal["solved", "nothing_to_do", "unsatisfiable", "refused"]


@dataclass(frozen=True)
class Slot:
    owner_kind: str  # "bus" or "device"
    owner_id: str
    role: str
    assignment: PinAssignment

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.owner_kind, self.owner_id, self.role)

    @property
    def path(self) -> str:
        section = "buses" if self.owner_kind == "bus" else "devices"
        return f"{section}.{self.owner_id}.{self.role}"

    def describe(self) -> str:
        return f"{self.owner_kind} '{self.owner_id}' ({self.role})"


@dataclass(frozen=True)
class Option:
    pin: str
    score: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class Assignment:
    slot: Slot
    pin: str
    score: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class SolveResult:
    status: Status
    file: str
    assignments: tuple[Assignment, ...] = ()
    report: Report | None = None  # check of the solved file
    messages: tuple[str, ...] = ()
    spec: HardwareSpec | None = field(default=None, repr=False, compare=False)

    @property
    def exit_code(self) -> int:
        return 0 if self.status in ("solved", "nothing_to_do") else 2


def _num(pin: str) -> int:
    return int(pin.removeprefix("GPIO"))


def slots(spec: HardwareSpec, *, reassign: bool = False) -> list[Slot]:
    """Open slots in file order: ``auto`` pins, plus unlocked solver pins with ``reassign``."""
    found: list[Slot] = []
    owners: list[tuple[str, str, dict[str, PinAssignment]]] = [
        ("bus", b.id, b.pins) for b in spec.buses.values()
    ] + [("device", d.id, d.pins) for d in spec.devices.values()]
    for kind, owner, pins in owners:
        for role, a in pins.items():
            if a.auto or (reassign and a.origin == "solver" and not a.locked):
                found.append(Slot(kind, owner, role, a))
    return sorted(found, key=lambda s: (s.assignment.loc.line, s.assignment.loc.col))


def with_pins(spec: HardwareSpec, chosen: dict[tuple[str, str, str], str]) -> HardwareSpec:
    """A copy of ``spec`` with the given slots set to ``{pin, origin: solver}``."""

    def fill(kind: str, owner: str, pins: dict[str, PinAssignment]) -> dict[str, PinAssignment]:
        out = dict(pins)
        for role, a in pins.items():
            pin = chosen.get((kind, owner, role))
            if pin is not None:
                out[role] = PinAssignment(pin, "solver", False, a.loc)
        return out

    buses: dict[str, Bus] = {
        k: dataclasses.replace(b, pins=fill("bus", b.id, b.pins)) for k, b in spec.buses.items()
    }
    devices: dict[str, Device] = {
        k: dataclasses.replace(d, pins=fill("device", d.id, d.pins))
        for k, d in spec.devices.items()
    }
    return dataclasses.replace(spec, buses=buses, devices=devices)


class _Problem:
    def __init__(self, base: LoadResult, spec: HardwareSpec, db: ChipDB, chip: ChipData) -> None:
        self.base = base
        self.spec = spec
        self.db = db
        self.chip = chip
        # Pins already taken by assignments the solver keeps.
        assigned = [
            *(b.pins for b in spec.buses.values()),
            *(d.pins for d in spec.devices.values()),
        ]
        self.fixed = {a.pin for pins in assigned for a in pins.values() if not a.auto}

    def run(self, spec: HardwareSpec) -> Report:
        return check(LoadResult(self.base.file, (), spec, self.base.document), self.db)

    def _bonus(self, slot: Slot, pin: str) -> tuple[int, list[str]]:
        score, reasons = 0, []
        signal = self._spi_signal(slot)
        if signal is not None:
            host, name = signal
            if self.chip.spi_iomux.get(host, {}).get(name) == pin:
                score += IOMUX_BONUS
                reasons.append(f"{host} IO_MUX pin for {name.upper()}")
        info = self.chip.pin(pin)
        if info is not None and info.strap is not None:
            score -= SPECIAL_PIN_PENALTY
            reasons.append(f"strapping pin ({info.strap.function}), used as a last resort")
        for group in sorted(info.groups if info is not None else {}):
            score -= SPECIAL_PIN_PENALTY
            reasons.append(f"shares {group.removesuffix('_pins')} function, used as a last resort")
        if (
            slot.owner_kind == "device"
            and self.spec.uses is not None
            and "deep_sleep" in self.spec.uses
            and info is not None
            and info.rtc_channel is not None
        ):
            score += RTC_BONUS
            reasons.append("RTC-capable pin (deep sleep in use)")
        if info is not None and info.adc is not None and self._is_adc(slot):
            reasons.append(f"{info.adc[0].upper()} channel {info.adc[1]}")
        return score, reasons

    def _is_adc(self, slot: Slot) -> bool:
        dev = self.spec.devices.get(slot.owner_id) if slot.owner_kind == "device" else None
        return dev is not None and dev.kind == "adc"

    def _spi_signal(self, slot: Slot) -> tuple[str, str] | None:
        if slot.owner_kind == "bus":
            own = self.spec.buses[slot.owner_id]
            if own.kind == "spi" and slot.role in _SPI_SIGNALS:
                return (own.host or "SPI2", _SPI_SIGNALS[slot.role])
            return None
        dev = self.spec.devices[slot.owner_id]
        if slot.role == "cs" and dev.bus is not None:
            parent = self.spec.buses.get(dev.bus)
            if parent is not None and parent.kind == "spi":
                return (parent.host or "SPI2", "cs")
        return None

    def options(self, slot: Slot) -> tuple[list[Option], Counter[str]]:
        """Feasible pins for ``slot`` (best first) and why the others were rejected."""
        feasible: list[Option] = []
        rejected: Counter[str] = Counter()
        for name in sorted(self.chip.pins, key=_num):
            if name in self.fixed:
                rejected["used by another fixed pin"] += 1
                continue
            report = self.run(with_pins(self.spec, {slot.key: name}))
            hits = [f for f in report.active if f.diagnostic.path == slot.path]
            errors = sorted({f.rule_id for f in hits if f.severity == "error"})
            if errors:
                for rule_id in errors:
                    rejected[rule_id] += 1
                continue
            warnings = sorted({f.rule_id for f in hits if f.severity == "warning"})
            infos = sorted({f.rule_id for f in hits if f.severity == "info"})
            bonus, reasons = self._bonus(slot, name)
            score = bonus - WARNING_PENALTY * len(warnings) - INFO_PENALTY * len(infos)
            reasons += [f"accepted {r}" for r in warnings + infos]
            feasible.append(Option(name, score, tuple(reasons) or ("free pin with no findings",)))
        feasible.sort(key=lambda o: (-o.score, _num(o.pin)))
        return feasible, rejected


def _search(problem: _Problem, table: list[tuple[Slot, list[Option]]]) -> list[Option] | None:
    best: list[Option] | None = None
    best_score: int | None = None
    leaves = 0
    # Upper bound of what the remaining slots can still add.
    tail_max = [0] * (len(table) + 1)
    for i in range(len(table) - 1, -1, -1):
        tail_max[i] = tail_max[i + 1] + (table[i][1][0].score if table[i][1] else 0)

    def visit(depth: int, chosen: list[Option], used: set[str], score: int) -> None:
        nonlocal best, best_score, leaves
        if leaves >= MAX_LEAVES:
            return
        if best_score is not None and score + tail_max[depth] <= best_score:
            return
        if depth == len(table):
            leaves += 1
            spec = with_pins(
                problem.spec, {s.key: o.pin for (s, _), o in zip(table, chosen, strict=True)}
            )
            if problem.run(spec).status != "error":
                best, best_score = list(chosen), score
            return
        for option in table[depth][1]:
            if option.pin in used:
                continue
            used.add(option.pin)
            chosen.append(option)
            visit(depth + 1, chosen, used, score + option.score)
            chosen.pop()
            used.remove(option.pin)

    visit(0, [], set(), 0)
    return best


def _pre_errors(problem: _Problem, open_keys: set[str]) -> list[str]:
    """Errors in the file that the solver cannot fix (not on an open slot)."""
    report = problem.run(problem.spec)
    return [
        str(f)
        for f in report.active
        if f.severity == "error" and f.rule_id != SOLVE_ID and f.diagnostic.path not in open_keys
    ]


def solve(base: LoadResult, db: ChipDB | None = None, *, reassign: bool = False) -> SolveResult:
    """Fill the open slots of a loaded ``hardware.yaml``."""
    db = db if db is not None else ChipDB()
    if base.spec is None:
        return SolveResult("refused", base.file, messages=tuple(str(d) for d in base.diagnostics))
    spec = base.spec
    module = db.module(spec.module)
    chip = db.chip(module.chip) if module is not None else None
    if module is None or chip is None:
        return SolveResult("refused", base.file, messages=(f"no chip data for '{spec.module}'",))
    open_slots = slots(spec, reassign=reassign)
    # Reassigned slots become auto so their old pins do not block anything.
    spec = _as_auto(spec, {s.key for s in open_slots})
    problem = _Problem(base, spec, db, chip)
    blocking = _pre_errors(problem, {s.path for s in open_slots})
    if blocking:
        return SolveResult("refused", base.file, messages=("fix these errors first:", *blocking))
    if not open_slots:
        return SolveResult("nothing_to_do", base.file, report=problem.run(spec), spec=spec)

    table: list[tuple[Slot, list[Option]]] = []
    for slot in open_slots:
        feasible, rejected = problem.options(slot)
        if not feasible:
            return SolveResult(
                "unsatisfiable", base.file, messages=_explain(slot, rejected, len(chip.pins))
            )
        table.append((slot, feasible))
    # Most constrained first; file order breaks ties.
    order = sorted(range(len(table)), key=lambda i: (len(table[i][1]), i))
    ordered = [table[i] for i in order]
    found = _search(problem, ordered)
    if found is None:
        return SolveResult("unsatisfiable", base.file, messages=_explain_conflict(ordered))
    picks = {slot.key: option for (slot, _), option in zip(ordered, found, strict=True)}
    assignments = tuple(
        Assignment(s, picks[s.key].pin, picks[s.key].score, picks[s.key].reasons)
        for s in open_slots
    )
    solved = with_pins(spec, {k: o.pin for k, o in picks.items()})
    return SolveResult("solved", base.file, assignments, problem.run(solved), spec=solved)


def _as_auto(spec: HardwareSpec, keys: set[tuple[str, str, str]]) -> HardwareSpec:
    """A copy of ``spec`` with the given slots reset to ``auto``."""

    def reset(kind: str, owner: str, pins: dict[str, PinAssignment]) -> dict[str, PinAssignment]:
        return {
            role: PinAssignment(AUTO, "user", False, a.loc) if (kind, owner, role) in keys else a
            for role, a in pins.items()
        }

    buses = {
        k: dataclasses.replace(b, pins=reset("bus", b.id, b.pins)) for k, b in spec.buses.items()
    }
    devices = {
        k: dataclasses.replace(d, pins=reset("device", d.id, d.pins))
        for k, d in spec.devices.items()
    }
    return dataclasses.replace(spec, buses=buses, devices=devices)


def _explain(slot: Slot, rejected: Counter[str], total: int) -> tuple[str, ...]:
    lines = [
        f"no pin satisfies {slot.describe()} at {slot.path}; all {total} GPIOs rejected "
        "(a pin can fail several rules):"
    ]
    lines += [f"  {reason}: {count}" for reason, count in sorted(rejected.items())]
    return tuple(lines)


def _explain_conflict(table: Iterable[tuple[Slot, list[Option]]]) -> tuple[str, ...]:
    rows = list(table)
    pins = sorted({o.pin for _, opts in rows for o in opts}, key=_num)
    lines = [
        f"{len(rows)} slots compete for {len(pins)} usable pins and no combination passes check:"
    ]
    lines += [f"  {s.path}: {', '.join(o.pin for o in opts)}" for s, opts in rows]
    return tuple(lines)
