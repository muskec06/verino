"""Typed, read-only access to ``chipdata/`` (chips, modules, parts, boards, ESP-IDF facts).

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
    io_input_max_volts: float | None = None
    spi_iomux: dict[str, dict[str, str]] = field(default_factory=dict)  # host -> signal -> pin

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
    flash_size: str | None = None
    flash_interface: str | None = None
    flash_max_freq_mhz: int | None = None
    psram_size: str | None = None
    psram_interface: str | None = None


@dataclass(frozen=True)
class PresetPartition:
    name: str
    type: str
    subtype: str
    size: str


@dataclass(frozen=True)
class PartitionData:
    """ESP-IDF partition table facts (``chipdata/idf/partitions.yaml``)."""

    table_offset: int
    table_size: int
    sector_size: int
    app_align: int
    ota_app_subtypes: tuple[str, ...]
    ota_data_subtype: str
    presets: dict[str, tuple[PresetPartition, ...]]
    idf_source: str


@dataclass(frozen=True)
class PartPin:
    direction: str
    level: str | None = None


@dataclass(frozen=True)
class PartData:
    part: str
    title: str
    kinds: tuple[str, ...]
    supply: tuple[float, float] | None
    supply_kind: str | None
    pins: dict[str, PartPin]
    reset_imposes: dict[str, str]
    actuator: bool = False
    safe_boot_level: str | None = None


def _part_from_doc(doc: Any) -> PartData:
    manual = doc["manual"]
    supply = manual.get("supply")
    actuator = manual.get("actuator") or {}
    return PartData(
        part=str(doc["part"]),
        title=str(doc["title"]),
        kinds=tuple(str(k) for k in manual["interface"]["kinds"]),
        supply=(float(supply["min_volts"]), float(supply["max_volts"])) if supply else None,
        supply_kind=str(supply["provenance"]["kind"]) if supply else None,
        pins={
            str(role): PartPin(str(p["direction"]), str(p["level"]) if "level" in p else None)
            for role, p in ((manual.get("pins") or {}).get("roles") or {}).items()
        },
        reset_imposes={
            str(role): str(level)
            for role, level in ((manual.get("reset_imposes") or {}).get("roles") or {}).items()
        },
        actuator=bool(actuator.get("value", False)),
        safe_boot_level=str(actuator["safe_boot_level"]) if "safe_boot_level" in actuator else None,
    )


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
        spi_iomux={
            str(host): {str(s): str(p) for s, p in signals.items()}
            for host, signals in (caps.get("spi_iomux") or {}).items()
        },
        io_input_max_volts=(
            float(manual["io_voltage"]["input_max_volts"]) if "io_voltage" in manual else None
        ),
    )


def _partitions_from_doc(doc: Any) -> PartitionData:
    table = doc["manual"]["table"]
    ota = doc["manual"]["ota"]
    generated = doc["generated"]
    return PartitionData(
        table_offset=int(table["offset"]),
        table_size=int(table["size"]),
        sector_size=int(table["sector_size"]),
        app_align=int(table["app_align"]),
        ota_app_subtypes=tuple(str(s) for s in ota["app_subtypes"]),
        ota_data_subtype=str(ota["data_subtype"]),
        presets={
            str(name): tuple(
                PresetPartition(str(p["name"]), str(p["type"]), str(p["subtype"]), str(p["size"]))
                for p in preset["partitions"]
            )
            for name, preset in generated["presets"].items()
        },
        idf_source=str(generated["provenance"]["source"]),
    )


def _module_from_doc(doc: Any) -> ModuleData:
    manual = doc["manual"]
    vdd = manual["memory"].get("vdd_spi_volts")
    flash = manual["memory"]["flash"]
    psram = manual["memory"].get("psram") or {}
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
        flash_size=str(flash["size"]),
        flash_interface=str(flash["interface"]),
        flash_max_freq_mhz=int(flash["max_freq_mhz"]) if "max_freq_mhz" in flash else None,
        psram_size=str(psram["size"]) if "size" in psram else None,
        psram_interface=str(psram["interface"]) if "interface" in psram else None,
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

    @functools.cache  # noqa: B019
    def part(self, part: str) -> PartData | None:
        doc = self._doc("parts", f"{part}.yaml")
        return _part_from_doc(doc) if doc is not None else None

    @functools.cache  # noqa: B019
    def partitions(self) -> PartitionData:
        doc = self._doc("idf", "partitions.yaml")
        if doc is None:
            raise FileNotFoundError(self.root / "idf" / "partitions.yaml")
        return _partitions_from_doc(doc)

    @functools.cache  # noqa: B019
    def version(self) -> str:
        """Chip data release (``sources.yaml`` ``version``), e.g. ``2026.11``."""
        doc = self._doc("sources.yaml")
        if doc is None:
            raise FileNotFoundError(self.root / "sources.yaml")
        return str(doc["version"])

    def has_board(self, board: str) -> bool:
        return (self.root / "boards" / f"{board}.yaml").is_file()

    def modules(self) -> list[str]:
        return sorted(p.stem for p in (self.root / "modules").glob("*.yaml"))
