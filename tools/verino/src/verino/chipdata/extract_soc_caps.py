"""Extract chip facts from an ESP-IDF source tree into the ``soc_caps`` block of a chip file.

Usage::

    python -m verino.chipdata.extract_soc_caps --idf <esp-idf> --chip esp32s3 \
        --out chipdata/chips/esp32s3.yaml

Only the ``soc_caps`` block is written; ``manual`` and comments are preserved.
Counts are stored raw under their ESP-IDF macro names (change note 0002).
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from verino.chipdata.cmacros import MacroError, evaluate, parse_defines
from verino.model.yamlio import dump_text, load_text

GENERATOR = "verino.chipdata.extract_soc_caps"
VERSION_HEADER = "components/esp_common/include/esp_idf_version.h"

_ADC = re.compile(r"^ADC(\d)_GPIO(\d+)_CHANNEL$")
_RTCIO = re.compile(r"^RTCIO_GPIO(\d+)_CHANNEL$")

# Raw counts exported for the rules, in output order. ESP-IDF v6 layout.
_MACROS = (
    "SOC_GPIO_PIN_COUNT",
    "SOC_I2C_NUM",
    "SOC_UART_NUM",
    "SOC_UART_HP_NUM",
    "SOC_SPI_PERIPH_NUM",
    "SOC_LEDC_TIMER_NUM",
    "SOC_LEDC_CHANNEL_NUM",
    "SOC_ADC_PERIPH_NUM",
    "SOC_RTCIO_PIN_COUNT",
    "SOC_TWAI_CONTROLLER_NUM",
    "PCNT_LL_INST_NUM",
    "PCNT_LL_UNITS_PER_INST",
    "RMT_LL_INST_NUM",
    "RMT_LL_CHANS_PER_INST",
    "RMT_LL_TX_CANDIDATES_PER_INST",
    "RMT_LL_RX_CANDIDATES_PER_INST",
)

_FIXED_PINS = (
    ("usb_dm", "USBPHY_DM_NUM"),
    ("usb_dp", "USBPHY_DP_NUM"),
    ("uart0_tx", "U0TXD_GPIO_NUM"),
    ("uart0_rx", "U0RXD_GPIO_NUM"),
)


class ExtractError(RuntimeError):
    """The ESP-IDF tree does not provide what the extractor expects."""


@dataclass(frozen=True)
class ChipConfig:
    chip: str
    caps_headers: tuple[str, ...]
    adc_header: str
    rtc_io_header: str
    fixed_pins: tuple[tuple[str, str], ...] = _FIXED_PINS
    macros: tuple[str, ...] = _MACROS

    @property
    def headers(self) -> tuple[str, ...]:
        return (*self.caps_headers, self.adc_header, self.rtc_io_header)


def chip_config(chip: str) -> ChipConfig:
    """Header layout of an ESP-IDF v6 tree for ``chip``."""
    soc = f"components/soc/{chip}/include/soc"
    return ChipConfig(
        chip=chip,
        caps_headers=(
            f"{soc}/soc_caps.h",
            f"{soc}/usb_pins.h",
            f"{soc}/uart_pins.h",
            f"components/esp_hal_pcnt/{chip}/include/hal/pcnt_ll.h",
            f"components/esp_hal_rmt/{chip}/include/hal/rmt_ll.h",
        ),
        adc_header=f"{soc}/adc_channel.h",
        rtc_io_header=f"{soc}/rtc_io_channel.h",
    )


# Chips with data in this phase. ESP32 is added in T8.
CHIPS: dict[str, ChipConfig] = {"esp32s3": chip_config("esp32s3")}


def _read(idf: Path, rel: str) -> dict[str, str]:
    path = idf / rel
    if not path.is_file():
        raise ExtractError(f"{rel} not found under {idf}")
    return parse_defines(path.read_text(encoding="utf-8", errors="replace"))


def _value(name: str, defines: dict[str, str]) -> int:
    if name not in defines:
        raise ExtractError(f"macro {name} not found")
    try:
        return evaluate(name, defines)
    except MacroError as exc:
        raise ExtractError(f"cannot evaluate {name}: {exc}") from exc


def _flow_seq(items: list[str]) -> CommentedSeq:
    seq = CommentedSeq(items)
    seq.fa.set_flow_style()
    return seq


def _flow_map(items: dict[str, Any]) -> CommentedMap:
    cmap = CommentedMap(items)
    cmap.fa.set_flow_style()
    return cmap


def _gpio_list(mask: int, count: int) -> CommentedSeq:
    return _flow_seq([f"GPIO{n}" for n in range(count) if mask >> n & 1])


def _commit(idf: Path) -> str | None:
    head = idf / ".git" / "HEAD"
    if not head.is_file():
        return None
    ref = head.read_text(encoding="utf-8").strip()
    if not ref.startswith("ref: "):
        return ref if re.fullmatch(r"[0-9a-f]{40}", ref) else None
    target = idf / ".git" / ref[5:]
    if target.is_file():
        return target.read_text(encoding="utf-8").strip()
    return None


def extract(idf: Path, config: ChipConfig) -> CommentedMap:
    """Build the ``soc_caps`` block for ``config.chip`` from the tree at ``idf``."""
    version_defs = _read(idf, VERSION_HEADER)
    version = "v{}.{}.{}".format(
        *(_value(f"ESP_IDF_VERSION_{p}", version_defs) for p in ("MAJOR", "MINOR", "PATCH"))
    )

    caps: dict[str, str] = {}
    for rel in config.caps_headers:
        caps.update(_read(idf, rel))
    adc_defs = _read(idf, config.adc_header)
    rtc_defs = _read(idf, config.rtc_io_header)

    count = _value("SOC_GPIO_PIN_COUNT", caps)
    adc: dict[str, dict[int, int]] = {}
    for name in adc_defs:
        match = _ADC.match(name)
        if match:
            unit = f"adc{match.group(1)}"
            adc.setdefault(unit, {})[int(match.group(2))] = _value(name, adc_defs)
    rtc: dict[int, int] = {}
    for name in rtc_defs:
        match = _RTCIO.match(name)
        if match:
            rtc[int(match.group(1))] = _value(name, rtc_defs)

    provenance = CommentedMap()
    provenance["kind"] = "soc_caps"
    provenance["source"] = f"esp-idf@{version}"
    provenance["idf_version"] = version
    commit = _commit(idf)
    if commit is not None:
        provenance["commit"] = commit
    provenance["files"] = sorted({VERSION_HEADER, *config.headers})
    provenance["generated_by"] = GENERATOR

    block = CommentedMap()
    block["provenance"] = provenance
    gpio = CommentedMap()
    gpio["count"] = count
    gpio["valid"] = _gpio_list(_value("SOC_GPIO_VALID_GPIO_MASK", caps), count)
    gpio["output"] = _gpio_list(_value("SOC_GPIO_VALID_OUTPUT_GPIO_MASK", caps), count)
    block["gpio"] = gpio
    block["adc"] = CommentedMap(
        (unit, _flow_map({f"GPIO{g}": ch for g, ch in sorted(adc[unit].items())}))
        for unit in sorted(adc)
    )
    block["rtc_io"] = _flow_map({f"GPIO{g}": ch for g, ch in sorted(rtc.items())})
    block["fixed_pins"] = _flow_map(
        {key: f"GPIO{_value(macro, caps)}" for key, macro in config.fixed_pins}
    )
    block["macros"] = CommentedMap((name, _value(name, caps)) for name in config.macros)
    return block


def update_chip_file(path: Path, chip: str, block: CommentedMap) -> None:
    """Write ``block`` as ``soc_caps`` into ``path``; other content is left untouched."""
    if path.is_file():
        doc = load_text(path.read_text(encoding="utf-8"))
        if doc.get("chip") != chip:
            raise ExtractError(f"{path} describes chip '{doc.get('chip')}', not '{chip}'")
    else:
        doc = CommentedMap()
        doc["schema"] = "verino-chip/1"
        doc["chip"] = chip
    if "soc_caps" in doc:
        doc["soc_caps"] = block
    else:
        doc.insert(list(doc).index("chip") + 1, "soc_caps", block)
    path.write_text(dump_text(doc), encoding="utf-8", newline="\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m " + GENERATOR, description=__doc__)
    parser.add_argument("--idf", type=Path, required=True, help="ESP-IDF source tree")
    parser.add_argument("--chip", required=True, help="chip id, e.g. esp32s3")
    parser.add_argument("--out", type=Path, required=True, help="chip file to update")
    args = parser.parse_args(argv)
    config = CHIPS.get(args.chip) or chip_config(args.chip)
    try:
        block = extract(args.idf, config)
        update_chip_file(args.out, args.chip, block)
    except ExtractError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"{args.out}: soc_caps for {args.chip} from ESP-IDF {block['provenance']['idf_version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
