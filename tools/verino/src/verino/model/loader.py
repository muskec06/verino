"""Read ``hardware.yaml``: YAML → schema validation → reference checks → typed model."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import Any, cast

from ruamel.yaml.error import YAMLError

from verino.model.diagnostics import SCHEMA_ERROR, YAML_ERROR, Diagnostic
from verino.model.schema import format_path, locate, validate
from verino.model.types import (
    Ack,
    Bus,
    BusKind,
    Device,
    DeviceKind,
    FlashConfig,
    HardwareSpec,
    Location,
    Memory,
    Origin,
    Partition,
    Partitions,
    PinAssignment,
    PsramConfig,
    Reserved,
    Use,
    Validation,
    ValidationStatus,
)
from verino.model.yamlio import load_text

_DEVICE_FIELDS = frozenset({"part", "bus", "kind", "addr", "freq_hz"})
_BUS_PIN_ROLES = ("sda", "scl", "sclk", "mosi", "miso", "tx", "rx", "rts", "cts")


@dataclass(frozen=True)
class LoadResult:
    """Outcome of reading a file. ``spec`` is ``None`` when any error was found."""

    file: str
    diagnostics: tuple[Diagnostic, ...]
    spec: HardwareSpec | None = None
    document: Any = field(default=None, repr=False, compare=False)

    @property
    def ok(self) -> bool:
        return self.spec is not None


def load_hardware(path: str | Path) -> LoadResult:
    """Read and validate a ``hardware.yaml`` file."""
    text = Path(path).read_text(encoding="utf-8")
    return parse_hardware(text, PurePath(path).as_posix())


def parse_hardware(text: str, file: str = "hardware.yaml") -> LoadResult:
    """Parse and validate ``hardware.yaml`` text; ``file`` is used in locations."""
    try:
        doc = load_text(text)
    except YAMLError as exc:
        mark = getattr(exc, "problem_mark", None) or getattr(exc, "context_mark", None)
        line = mark.line + 1 if mark is not None else 1
        col = mark.column + 1 if mark is not None else 1
        problem = getattr(exc, "problem", None) or str(exc).splitlines()[0]
        diag = Diagnostic(
            YAML_ERROR,
            Location(file, line, col),
            "(yaml)",
            f"cannot parse YAML: {problem}",
            "The file must be valid YAML before any rule can run.",
            "correct the syntax near this position.",
        )
        return LoadResult(file, (diag,))

    diags = validate(doc, file)
    if not diags:
        diags = _check_references(doc, file)
    if diags:
        return LoadResult(file, tuple(diags), None, doc)
    return LoadResult(file, (), _Builder(doc, file).spec(), doc)


def _check_references(doc: Any, file: str) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    buses = doc.get("buses") or {}
    devices = doc.get("devices") or {}
    for dev_id, dev in devices.items():
        bus = dev.get("bus")
        if bus is not None and bus not in buses:
            known = ", ".join(buses) or "none"
            diags.append(
                Diagnostic(
                    SCHEMA_ERROR,
                    locate(doc, ["devices", dev_id, "bus"], file),
                    format_path(["devices", dev_id, "bus"]),
                    f"device '{dev_id}' refers to bus '{bus}', which is not defined",
                    "The device has no bus pins to talk on.",
                    f"define buses.{bus} or use one of: {known}.",
                )
            )
    for index, ack in enumerate(doc.get("ack") or []):
        device = ack.get("device")
        if device is not None and device not in devices:
            diags.append(
                Diagnostic(
                    SCHEMA_ERROR,
                    locate(doc, ["ack", index, "device"], file),
                    format_path(["ack", index, "device"]),
                    f"ack refers to device '{device}', which is not defined",
                    "An acknowledgement must point at something that exists.",
                    "fix the device id or remove the acknowledgement.",
                )
            )
    for index, entry in enumerate(doc.get("reserved") or []):
        pins = entry["pins"]
        if isinstance(pins, str):
            first, last = (int(p.removeprefix("GPIO")) for p in pins.split("-"))
            if first > last:
                diags.append(
                    Diagnostic(
                        SCHEMA_ERROR,
                        locate(doc, ["reserved", index, "pins"], file),
                        format_path(["reserved", index, "pins"]),
                        f"range '{pins}' is reversed",
                        "Ranges run from the lower to the higher pin number.",
                        f"write GPIO{last}-GPIO{first}.",
                    )
                )
    return sorted(diags, key=Diagnostic.sort_key)


def _opt_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _opt_int(value: Any) -> int | None:
    return None if value is None else int(value)


class _Builder:
    """Converts a schema-valid ruamel document into the typed model."""

    def __init__(self, doc: Any, file: str) -> None:
        self.doc = doc
        self.file = file

    def loc(self, *path: str | int) -> Location:
        return locate(self.doc, list(path), self.file)

    def spec(self) -> HardwareSpec:
        d = self.doc
        return HardwareSpec(
            schema=str(d["schema"]),
            module=str(d["module"]),
            loc=Location(self.file, 1, 1),
            source=str(d.get("source", "native")),
            board=_opt_str(d.get("board")),
            board_rev=_opt_str(d.get("board_rev")),
            chip_rev=_opt_str(d.get("chip_rev")),
            hw_rev=_opt_str(d.get("hw_rev")),
            uses=tuple(cast(Use, str(u)) for u in d["uses"]) if "uses" in d else None,
            memory=self.memory(d["memory"]) if "memory" in d else None,
            buses={str(k): self.bus(str(k), v) for k, v in (d.get("buses") or {}).items()},
            devices={str(k): self.device(str(k), v) for k, v in (d.get("devices") or {}).items()},
            ack=tuple(self.ack(i, a) for i, a in enumerate(d.get("ack") or [])),
            reserved=tuple(self.reserved(i, r) for i, r in enumerate(d.get("reserved") or [])),
            validation=self.validation(d["validation"]) if "validation" in d else None,
        )

    def pin(self, value: Any, *path: str | int) -> PinAssignment:
        loc = self.loc(*path)
        if isinstance(value, str):
            return PinAssignment(
                pin=str(value), origin="user", locked=False, loc=loc, shorthand=True
            )
        return PinAssignment(
            pin=str(value["pin"]),
            origin=cast(Origin, str(value["origin"])),
            locked=bool(value.get("locked", False)),
            loc=loc,
        )

    def memory(self, m: Any) -> Memory:
        flash = m.get("flash")
        psram = m.get("psram")
        parts = m.get("partitions")
        return Memory(
            loc=self.loc("memory"),
            flash=FlashConfig(
                loc=self.loc("memory", "flash"),
                size=_opt_str(flash.get("size")),
                mode=_opt_str(flash.get("mode")),
                freq=_opt_str(flash.get("freq")),
                origin=_opt_str(flash.get("origin")),
            )
            if flash is not None
            else None,
            psram=PsramConfig(
                loc=self.loc("memory", "psram"),
                size=_opt_str(psram.get("size")),
                mode=_opt_str(psram.get("mode")),
                freq=_opt_str(psram.get("freq")),
                origin=_opt_str(psram.get("origin")),
            )
            if psram is not None
            else None,
            cpu_freq_mhz=_opt_int(m.get("cpu_freq_mhz")),
            partitions=Partitions(
                loc=self.loc("memory", "partitions"),
                preset=_opt_str(parts.get("preset")),
                custom=tuple(
                    Partition(
                        name=str(p["name"]),
                        type=str(p["type"]),
                        subtype=str(p["subtype"]),
                        size=str(p["size"]),
                        loc=self.loc("memory", "partitions", "custom", i),
                    )
                    for i, p in enumerate(parts.get("custom") or [])
                ),
            )
            if parts is not None
            else None,
        )

    def bus(self, bus_id: str, b: Any) -> Bus:
        return Bus(
            id=bus_id,
            kind=cast(BusKind, str(b["kind"])),
            loc=self.loc("buses", bus_id),
            pins={
                str(role): self.pin(value, "buses", bus_id, str(role))
                for role, value in b.items()
                if role in _BUS_PIN_ROLES
            },
            freq_hz=_opt_int(b.get("freq_hz")),
            pullups=_opt_str(b.get("pullups")),
            host=_opt_str(b.get("host")),
            baud=_opt_int(b.get("baud")),
        )

    def device(self, dev_id: str, v: Any) -> Device:
        return Device(
            id=dev_id,
            part=str(v["part"]),
            loc=self.loc("devices", dev_id),
            bus=_opt_str(v.get("bus")),
            kind=cast(DeviceKind | None, _opt_str(v.get("kind"))),
            addr=_opt_int(v.get("addr")),
            freq_hz=_opt_int(v.get("freq_hz")),
            pins={
                str(role): self.pin(value, "devices", dev_id, str(role))
                for role, value in v.items()
                if role not in _DEVICE_FIELDS
            },
        )

    def ack(self, index: int, a: Any) -> Ack:
        return Ack(
            rule=str(a["rule"]),
            reason=str(a["reason"]),
            loc=self.loc("ack", index),
            pin=_opt_str(a.get("pin")),
            device=_opt_str(a.get("device")),
        )

    def reserved(self, index: int, r: Any) -> Reserved:
        raw = r["pins"]
        if isinstance(raw, str):
            first, last = (int(p.removeprefix("GPIO")) for p in raw.split("-"))
            pins = tuple(f"GPIO{n}" for n in range(first, last + 1))
        else:
            pins = tuple(str(p) for p in raw)
        return Reserved(pins=pins, why=str(r["why"]), loc=self.loc("reserved", index))

    def validation(self, v: Any) -> Validation:
        return Validation(
            tool=str(v["tool"]),
            chipdata=str(v["chipdata"]),
            status=cast(ValidationStatus, str(v["status"])),
            checksum=str(v["checksum"]),
            loc=self.loc("validation"),
            warnings=tuple(str(w) for w in v.get("warnings") or []),
        )
