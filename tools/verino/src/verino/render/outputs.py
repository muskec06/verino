"""Build the files of ``verino pins render`` from a checked ``hardware.yaml``.

Everything is rendered into memory first (path -> text) so tests can compare against
golden files and the CLI writes only when every output was produced.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined

from verino import __version__
from verino.chipdata.db import ChipData, ChipDB, ModuleData
from verino.chipdata.partitions import Placed, entries, format_size, layout, parse_size
from verino.model import LoadResult, load_hardware
from verino.model.types import HardwareSpec, PinAssignment
from verino.report.format import to_dict
from verino.report.writeback import pin_range, reserved_pins
from verino.rules import Report, check

PINS_HPP = "gen/pins.hpp"
SDKCONFIG = "gen/sdkconfig.defaults"
PARTITIONS_CSV = "gen/partitions.csv"
PINOUT_MD = "gen/pinout.md"
RENDER_SCHEMA = "verino-render/1"

# C++ keywords that are also valid bus/device ids (lowercase, [a-z][a-z0-9_]*).
_CPP_KEYWORDS_TEXT = (
    "alignas alignof and and_eq asm auto bitand bitor bool break case catch char char8_t "
    "char16_t char32_t class compl concept const consteval constexpr constinit const_cast "
    "continue co_await co_return co_yield decltype default delete do double dynamic_cast "
    "else enum explicit export extern false float for friend goto if inline int long "
    "mutable namespace new noexcept not not_eq nullptr operator or or_eq private protected "
    "public register reinterpret_cast requires return short signed sizeof static "
    "static_assert static_cast struct switch template this thread_local throw true try "
    "typedef typeid typename union unsigned using virtual void volatile wchar_t while xor "
    "xor_eq"
)
_CPP_KEYWORDS = frozenset(_CPP_KEYWORDS_TEXT.split())

_ENV = Environment(
    loader=PackageLoader("verino.render", "templates"),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=False,
)


@dataclass(frozen=True)
class Const:
    name: str
    value: str


@dataclass(frozen=True)
class Group:
    name: str
    comment: str
    consts: tuple[Const, ...]


@dataclass(frozen=True)
class PinRow:
    gpio: str
    owner: str
    role: str
    origin: str
    locked: bool


def _ident(name: str) -> str:
    return f"{name}_" if name in _CPP_KEYWORDS else name


def _gpio(assignment: PinAssignment) -> str:
    return str(int(assignment.pin.removeprefix("GPIO")))


def _groups(spec: HardwareSpec) -> list[Group]:
    groups: list[Group] = []
    for bus in spec.buses.values():
        consts = [Const(role.upper(), _gpio(a)) for role, a in bus.pins.items()]
        if bus.freq_hz is not None:
            consts.append(Const("FREQ_HZ", str(bus.freq_hz)))
        if bus.baud is not None:
            consts.append(Const("BAUD", str(bus.baud)))
        comment = f"{bus.kind} bus" + (f" on {bus.host}" if bus.host else "")
        groups.append(Group(_ident(bus.id), comment, tuple(consts)))
    for dev in spec.devices.values():
        consts = [Const(role.upper(), _gpio(a)) for role, a in dev.pins.items()]
        if dev.addr is not None:
            consts.append(Const("ADDR", f"0x{dev.addr:02x}"))
        if dev.freq_hz is not None:
            consts.append(Const("FREQ_HZ", str(dev.freq_hz)))
        where = f" on {dev.bus}" if dev.bus else f" ({dev.kind})" if dev.kind else ""
        groups.append(Group(_ident(dev.id), f"{dev.part}{where}", tuple(consts)))
    return groups


def _pin_rows(spec: HardwareSpec) -> list[PinRow]:
    rows = [
        PinRow(a.pin, f"bus {bus.id}", role, a.origin, a.locked)
        for bus in spec.buses.values()
        for role, a in bus.pins.items()
    ]
    rows += [
        PinRow(a.pin, f"device {dev.id} ({dev.part})", role, a.origin, a.locked)
        for dev in spec.devices.values()
        for role, a in dev.pins.items()
    ]
    return sorted(rows, key=lambda r: (int(r.gpio.removeprefix("GPIO")), r.owner, r.role))


def _sdkconfig(spec: HardwareSpec, module: ModuleData, has_table: bool) -> list[str]:
    """``CONFIG_*`` lines; symbol names are checked against ESP-IDF Kconfig in the tests."""
    memory = spec.memory
    flash = memory.flash if memory else None
    psram = memory.psram if memory else None
    lines: list[str] = []
    if flash is not None and flash.mode is not None:
        lines.append(f"CONFIG_ESPTOOLPY_FLASHMODE_{flash.mode.upper()}=y")
    if flash is not None and flash.freq is not None:
        lines.append(f"CONFIG_ESPTOOLPY_FLASHFREQ_{flash.freq.upper()}=y")
    flash_size = flash.size if flash is not None and flash.size else module.flash_size
    if flash_size is not None:
        lines.append(f"CONFIG_ESPTOOLPY_FLASHSIZE_{parse_size(flash_size) >> 20}MB=y")
    psram_mode = psram.mode if psram is not None and psram.mode else module.psram_interface
    if module.psram_size is not None:
        lines.append("CONFIG_SPIRAM=y")
        if psram_mode is not None:
            lines.append(f"CONFIG_SPIRAM_MODE_{'OCT' if psram_mode == 'octal' else 'QUAD'}=y")
        if psram is not None and psram.freq is not None:
            lines.append(f"CONFIG_SPIRAM_SPEED_{psram.freq.upper()}=y")
    if memory is not None and memory.cpu_freq_mhz is not None:
        lines.append(f"CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ_{memory.cpu_freq_mhz}=y")
    if has_table:
        lines.append("CONFIG_PARTITION_TABLE_CUSTOM=y")
        lines.append(f'CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="{PARTITIONS_CSV}"')
    return lines


def _table(spec: HardwareSpec, module: ModuleData, db: ChipDB) -> list[Placed]:
    memory = spec.memory
    if memory is None or memory.partitions is None:
        return []
    flash = memory.flash
    size = flash.size if flash is not None and flash.size else module.flash_size
    if size is None:
        return []
    data = db.partitions()
    return layout(entries(memory.partitions, data), data, parse_size(size))


def render(
    spec: HardwareSpec,
    file: str,
    status: str,
    module: ModuleData,
    chip: ChipData,
    db: ChipDB,
) -> dict[str, str]:
    """All outputs as ``{relative path: text}``; only call this for files without errors."""
    table = _table(spec, module, db)
    context = {
        "version": __version__,
        "source": PurePath(file).name,
        "module": module.module,
        "chip": chip.chip,
        "chipdata": f"{chip.chip}@{db.version()}",
        "status": status,
        "groups": _groups(spec),
        "pins": _pin_rows(spec),
        "reserved": [(pin_range(p) or ", ".join(p), why) for p, why in reserved_pins(chip, module)],
        "partitions": [
            {
                "name": p.entry.name,
                "type": p.entry.type,
                "subtype": p.entry.subtype,
                "offset": hex(p.offset),
                "size": format_size(p.size),
            }
            for p in table
        ],
        "sdkconfig": _sdkconfig(spec, module, bool(table)),
        "partitions_csv": PARTITIONS_CSV,
    }
    out = {
        PINS_HPP: _ENV.get_template("pins.hpp.j2").render(context),
        SDKCONFIG: _ENV.get_template("sdkconfig.defaults.j2").render(context),
        PINOUT_MD: _ENV.get_template("pinout.md.j2").render(context),
    }
    if table:
        out[PARTITIONS_CSV] = _ENV.get_template("partitions.csv.j2").render(context)
    return dict(sorted(out.items()))


@dataclass(frozen=True)
class RenderResult:
    report: Report
    files: dict[str, str]  # empty when the file could not be rendered
    reason: str = ""


def render_loaded(result: LoadResult, db: ChipDB | None = None) -> RenderResult:
    """Check a loaded ``hardware.yaml`` and render it when the check has no active errors."""
    db = db if db is not None else ChipDB()
    report = check(result, db)
    if result.spec is None or report.status == "error":
        return RenderResult(report, {}, "the check reports errors")
    module = db.module(result.spec.module)
    chip = db.chip(module.chip) if module is not None else None
    if module is None or chip is None:
        return RenderResult(report, {}, "no chip data for the module")
    return RenderResult(report, render(result.spec, result.file, report.status, module, chip, db))


def render_file(path: Path, db: ChipDB | None = None) -> RenderResult:
    """Check ``path`` and render it when the check has no active errors."""
    return render_loaded(load_hardware(path), db)


def write_outputs(result: RenderResult, root: Path) -> list[str]:
    """Write the rendered files below ``root``; returns the written paths."""
    written: list[str] = []
    for rel, text in result.files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
        written.append(target.as_posix())
    return written


def to_dict_result(result: RenderResult, written: list[str]) -> dict[str, Any]:
    """The ``verino-render/1`` JSON document."""
    return {
        "schema": RENDER_SCHEMA,
        "file": result.report.file,
        "written": written,
        "reason": result.reason or None,
        "report": to_dict(result.report),
    }
