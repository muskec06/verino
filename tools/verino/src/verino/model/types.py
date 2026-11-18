"""Typed model of a ``hardware.yaml`` file (schema ``verino-hw/1``).

Every object carries the :class:`Location` it was read from so that rules can point
at the exact line and column in the user's file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Origin = Literal["schematic", "user", "board_default", "solver", "cubemx"]
BusKind = Literal["i2c", "spi", "uart"]
DeviceKind = Literal["adc", "gpio", "onewire", "pwm"]
ValidationStatus = Literal["ok", "warnings", "error"]


@dataclass(frozen=True, order=True)
class Location:
    """1-based line and column in a source file."""

    file: str
    line: int
    col: int

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.col}"


@dataclass(frozen=True)
class PinAssignment:
    """A pin with its provenance. ``shorthand`` is true for bare device pin names."""

    pin: str
    origin: Origin
    locked: bool
    loc: Location
    shorthand: bool = False


@dataclass(frozen=True)
class FlashConfig:
    loc: Location
    size: str | None = None
    mode: str | None = None
    freq: str | None = None
    origin: str | None = None


@dataclass(frozen=True)
class PsramConfig:
    loc: Location
    size: str | None = None
    mode: str | None = None
    freq: str | None = None
    origin: str | None = None


@dataclass(frozen=True)
class Partition:
    name: str
    type: str
    subtype: str
    size: str
    loc: Location


@dataclass(frozen=True)
class Partitions:
    loc: Location
    preset: str | None = None
    custom: tuple[Partition, ...] = ()


@dataclass(frozen=True)
class Memory:
    loc: Location
    flash: FlashConfig | None = None
    psram: PsramConfig | None = None
    cpu_freq_mhz: int | None = None
    partitions: Partitions | None = None


@dataclass(frozen=True)
class Bus:
    """A bus instance. ``pins`` maps role (sda, scl, sclk, tx, ...) to assignment, in file order."""

    id: str
    kind: BusKind
    loc: Location
    pins: dict[str, PinAssignment] = field(default_factory=dict)
    freq_hz: int | None = None
    pullups: str | None = None
    host: str | None = None
    baud: int | None = None


@dataclass(frozen=True)
class Device:
    """A connected part. ``pins`` maps pin role (pin, cs, int, trig, ...) to assignment."""

    id: str
    part: str
    loc: Location
    bus: str | None = None
    kind: DeviceKind | None = None
    addr: int | None = None
    freq_hz: int | None = None
    pins: dict[str, PinAssignment] = field(default_factory=dict)


@dataclass(frozen=True)
class Ack:
    rule: str
    reason: str
    loc: Location
    pin: str | None = None
    device: str | None = None


@dataclass(frozen=True)
class Reserved:
    """Tool-written reservation; ranges are expanded to individual pin names."""

    pins: tuple[str, ...]
    why: str
    loc: Location


@dataclass(frozen=True)
class Validation:
    tool: str
    chipdata: str
    status: ValidationStatus
    checksum: str
    loc: Location
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class HardwareSpec:
    schema: str
    module: str
    loc: Location
    source: str = "native"
    board: str | None = None
    board_rev: str | None = None
    chip_rev: str | None = None
    hw_rev: str | None = None
    memory: Memory | None = None
    buses: dict[str, Bus] = field(default_factory=dict)
    devices: dict[str, Device] = field(default_factory=dict)
    ack: tuple[Ack, ...] = ()
    reserved: tuple[Reserved, ...] = ()
    validation: Validation | None = None
