"""Typed, read-only access to ``chipdata/`` (chips, modules, boards).

Chip files keep generated (``soc_caps``) and hand-written (``manual``) facts apart
(change note 0002); :class:`ChipData` merges them into a per-pin view for the rules.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

from verino.model.yamlio import load_text

# Pin groups from the ``manual`` block, by key.
PIN_GROUPS = ("spi_flash_pins", "octal_spi_pins", "usb_pins", "uart0_pins", "jtag_pins")


@dataclass(frozen=True)
class Strap:
    pin: str
    function: str
    default: str
    boot_safe: str
    on_violation: str
    severity: str
    ref: str


@dataclass(frozen=True)
class BootBehavior:
    state: str
    pull: str
    glitches: tuple[str, ...] = ()


@dataclass(frozen=True)
class PinInfo:
    name: str
    output: bool
    adc: tuple[str, int] | None = None
    rtc_channel: int | None = None
    strap: Strap | None = None
    boot: BootBehavior | None = None
    groups: dict[str, str] = field(default_factory=dict)  # group key -> signal name


@dataclass(frozen=True)
class ChipData:
    chip: str
    pins: dict[str, PinInfo]
    macros: dict[str, int]
    idf_source: str
    spi_hosts: tuple[str, ...] = ()
    adc2_wifi: str | None = None

    def pin(self, name: str) -> PinInfo | None:
        return self.pins.get(name)


@dataclass(frozen=True)
class ModuleData:
    module: str
    chip: str
    part_number: str
    exposed: frozenset[str]
    internal: dict[str, str]
    vdd_spi_volts: float | str | None = None


def _gpio_num(name: str) -> int:
    return int(name.removeprefix("GPIO"))


def _chip_from_doc(doc: Any) -> ChipData:
    caps = doc["soc_caps"]
    manual = doc.get("manual") or {}
    output = set(caps["gpio"]["output"])
    adc = {
        str(pin): (str(unit), int(ch))
        for unit, chans in caps["adc"].items()
        for pin, ch in chans.items()
    }
    rtc = {str(pin): int(ch) for pin, ch in caps["rtc_io"].items()}
    straps = {
        str(pin): Strap(
            pin=str(pin),
            function=str(s["function"]),
            default=str(s["default"]),
            boot_safe=str(s["boot_safe"]),
            on_violation=str(s["on_violation"]),
            severity=str(s["severity"]),
            ref=f"{s['provenance']['source']}, {s['provenance']['ref']}",
        )
        for pin, s in (manual.get("strapping") or {}).items()
    }
    boot = {
        str(pin): BootBehavior(
            state=str(b["state"]),
            pull=str(b["pull"]),
            glitches=tuple(str(g) for g in b.get("glitches") or []),
        )
        for pin, b in ((manual.get("boot_behavior") or {}).get("pins") or {}).items()
    }
    groups: dict[str, dict[str, str]] = {}
    for key in PIN_GROUPS:
        for pin, signal in ((manual.get(key) or {}).get("pins") or {}).items():
            groups.setdefault(str(pin), {})[key] = str(signal)
    pins = {
        str(name): PinInfo(
            name=str(name),
            output=name in output,
            adc=adc.get(str(name)),
            rtc_channel=rtc.get(str(name)),
            strap=straps.get(str(name)),
            boot=boot.get(str(name)),
            groups=groups.get(str(name), {}),
        )
        for name in sorted(caps["gpio"]["valid"], key=lambda n: _gpio_num(str(n)))
    }
    adc2 = manual.get("adc2_wifi")
    return ChipData(
        chip=str(doc["chip"]),
        pins=pins,
        macros={str(k): int(v) for k, v in caps["macros"].items()},
        idf_source=str(caps["provenance"]["source"]),
        spi_hosts=tuple(str(h) for h in (manual.get("spi_hosts") or {}).get("general_purpose", [])),
        adc2_wifi=str(adc2["behavior"]) if adc2 else None,
    )


def _module_from_doc(doc: Any) -> ModuleData:
    manual = doc["manual"]
    vdd = manual["memory"].get("vdd_spi_volts")
    return ModuleData(
        module=str(doc["module"]),
        chip=str(doc["chip"]),
        part_number=str(manual["part_number"]["value"]),
        exposed=frozenset(str(p) for p in manual["exposed_gpios"]["pins"]),
        internal={
            str(p): str(u)
            for p, u in ((manual.get("internal_pins") or {}).get("pins") or {}).items()
        },
        vdd_spi_volts=vdd if isinstance(vdd, (int, float, str)) else None,
    )


def default_root() -> Path:
    """``chipdata/`` shipped in the wheel, or the repository copy in a source checkout."""
    packaged = resources.files("verino") / "data" / "chipdata"
    if packaged.is_dir():
        return Path(str(packaged))
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "chipdata"
        if (candidate / "sources.yaml").is_file():
            return candidate
    raise FileNotFoundError("chipdata/ not found in the package or the repository")


class ChipDB:
    """Loads chip, module and board files on demand from a ``chipdata/`` root."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root if root is not None else default_root()

    def _doc(self, *parts: str) -> Any | None:
        path = self.root.joinpath(*parts)
        if not path.is_file():
            return None
        return load_text(path.read_text(encoding="utf-8"))

    @functools.cache  # noqa: B019 - one instance per process, small and immutable data
    def chip(self, chip: str) -> ChipData | None:
        doc = self._doc("chips", f"{chip}.yaml")
        return _chip_from_doc(doc) if doc is not None else None

    @functools.cache  # noqa: B019
    def module(self, module: str) -> ModuleData | None:
        doc = self._doc("modules", f"{module}.yaml")
        return _module_from_doc(doc) if doc is not None else None

    def has_board(self, board: str) -> bool:
        return (self.root / "boards" / f"{board}.yaml").is_file()

    def modules(self) -> list[str]:
        return sorted(p.stem for p in (self.root / "modules").glob("*.yaml"))
