"""Partition layout and size parsing."""

import pytest
from conftest import REPO_ROOT

from verino.chipdata.db import ChipDB
from verino.chipdata.partitions import TableEntry, format_size, layout, parse_size
from verino.model.types import Location

DATA = ChipDB(REPO_ROOT / "chipdata").partitions()
LOC = Location("hw.yaml", 1, 1)


@pytest.mark.parametrize(
    ("text", "size"),
    [
        ("0x6000", 0x6000),
        ("24K", 24576),
        ("24KB", 24576),
        ("1500K", 1536000),
        ("4M", 4 << 20),
        ("16MB", 16 << 20),
        ("4096", 4096),
    ],
)
def test_parse_size(text: str, size: int) -> None:
    assert parse_size(text) == size


def test_parse_size_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        parse_size("4 GB")


def test_format_size() -> None:
    assert (format_size(8 << 20), format_size(24576), format_size(0x1800)) == ("8M", "24K", "6K")
    assert format_size(100) == "0x64"


def test_two_ota_layout_matches_idf_documentation() -> None:
    # ESP-IDF v6.1.1 docs/en/api-guides/partition-tables.rst, "Factory app, two OTA definitions".
    table = tuple(
        TableEntry(p.name, p.type, p.subtype, p.size, LOC) for p in DATA.presets["two_ota"]
    )
    offsets = {p.entry.name: p.offset for p in layout(table, DATA, 4 << 20)}
    assert offsets == {
        "nvs": 0x9000,
        "otadata": 0xD000,
        "phy_init": 0xF000,
        "factory": 0x10000,
        "ota_0": 0x110000,
        "ota_1": 0x210000,
    }


def test_rest_runs_to_the_end_of_flash() -> None:
    table = (
        TableEntry("nvs", "data", "nvs", "24K", LOC),
        TableEntry("factory", "app", "factory", "1M", LOC),
        TableEntry("storage", "data", "spiffs", "rest", LOC),
    )
    last = layout(table, DATA, 4 << 20)[-1]
    assert (last.offset, last.end) == (0x110000, 4 << 20)
