"""What a rule sees: the hardware spec, its source document and the resolved chip data."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from verino.chipdata.db import ChipData, ChipDB, ModuleData
from verino.model.schema import format_path, locate
from verino.model.types import HardwareSpec, Location, PinAssignment

_CANONICAL = re.compile(r"^GPIO\d+$")


@dataclass(frozen=True)
class Hit:
    """One finding produced by a rule, before the engine adds the rule ID and ack state."""

    loc: Location
    path: str
    message: str
    why: str = ""
    fix: str = ""
    pin: str | None = None
    device: str | None = None


@dataclass(frozen=True)
class PinUse:
    """A pin assignment together with its owner (a bus or a device)."""

    owner_kind: str  # "bus" or "device"
    owner_id: str
    role: str
    assignment: PinAssignment

    @property
    def pin(self) -> str:
        return self.assignment.pin

    @property
    def canonical(self) -> bool:
        return _CANONICAL.match(self.pin) is not None

    @property
    def path(self) -> str:
        section = "buses" if self.owner_kind == "bus" else "devices"
        return format_path([section, self.owner_id, self.role])

    @property
    def device(self) -> str | None:
        return self.owner_id if self.owner_kind == "device" else None

    def describe(self) -> str:
        return f"{self.owner_kind} '{self.owner_id}' ({self.role})"

    def hit(self, message: str, why: str = "", fix: str = "") -> Hit:
        return Hit(self.assignment.loc, self.path, message, why, fix, self.pin, self.device)


@dataclass(frozen=True)
class Context:
    spec: HardwareSpec
    document: Any
    file: str
    db: ChipDB
    module: ModuleData | None
    chip: ChipData | None

    def loc(self, *path: str | int) -> Location:
        return locate(self.document, list(path), self.file)

    def key_loc(self, *path: str | int) -> Location:
        """Location of the key at ``path`` (for findings about a whole block)."""
        return locate(self.document, list(path), self.file, key=True)

    def pin_uses(self) -> list[PinUse]:
        """Every assigned pin in file order; ``auto`` slots are left out (see auto_uses)."""
        return [u for u in self._all_uses() if not u.assignment.auto]

    def auto_uses(self) -> list[PinUse]:
        """Pin slots still set to ``auto`` (to be filled by ``verino pins solve``)."""
        return [u for u in self._all_uses() if u.assignment.auto]

    def _all_uses(self) -> list[PinUse]:
        uses = [
            PinUse("bus", bus.id, role, assignment)
            for bus in self.spec.buses.values()
            for role, assignment in bus.pins.items()
        ]
        uses += [
            PinUse("device", dev.id, role, assignment)
            for dev in self.spec.devices.values()
            for role, assignment in dev.pins.items()
        ]
        return sorted(uses, key=lambda u: (u.assignment.loc.line, u.assignment.loc.col))

    def canonical_uses(self) -> list[PinUse]:
        """Pin uses with canonical GPIO names that exist on the chip."""
        if self.chip is None:
            return []
        return [u for u in self.pin_uses() if u.canonical and self.chip.pin(u.pin) is not None]

    def require_chip(self) -> ChipData:
        if self.chip is None:
            raise RuntimeError("rule needs chip data")
        return self.chip
