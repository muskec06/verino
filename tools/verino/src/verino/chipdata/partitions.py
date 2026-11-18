"""Partition table layout: where each partition of ``memory.partitions`` lands in flash.

Offsets follow the ESP-IDF rules in ``chipdata/idf/partitions.yaml``: the first partition
starts after the partition table, data partitions are sector-aligned and app partitions
are aligned to ``app_align`` (the same placement ``gen_esp32part.py`` uses for blank offsets).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from verino.chipdata.db import PartitionData
from verino.model.types import Location, Partitions

REST = "rest"
_SIZE = re.compile(r"^(?:0x(?P<hex>[0-9a-fA-F]+)|(?P<num>[0-9]+)(?P<unit>K|KB|M|MB)?)$")
_UNITS = {None: 1, "K": 1024, "KB": 1024, "M": 1024 * 1024, "MB": 1024 * 1024}


def parse_size(text: str) -> int:
    """Bytes for ``0x6000``, ``24K``, ``1500K``, ``4M`` or ``16MB`` (K and M are 1024-based)."""
    match = _SIZE.match(text.strip())
    if match is None:
        raise ValueError(f"not a size: {text!r}")
    if match["hex"] is not None:
        return int(match["hex"], 16)
    return int(match["num"]) * _UNITS[match["unit"]]


def format_size(size: int) -> str:
    """Short human form: ``4M``, ``24K`` or ``0x1800``."""
    if size % (1024 * 1024) == 0:
        return f"{size // (1024 * 1024)}M"
    if size % 1024 == 0:
        return f"{size // 1024}K"
    return hex(size)


@dataclass(frozen=True)
class TableEntry:
    """One requested partition, from ``custom`` or from a preset."""

    name: str
    type: str
    subtype: str
    size: str
    loc: Location


@dataclass(frozen=True)
class Placed:
    entry: TableEntry
    offset: int
    size: int

    @property
    def end(self) -> int:
        return self.offset + self.size


def entries(partitions: Partitions, data: PartitionData) -> tuple[TableEntry, ...]:
    """The table to use: ``custom`` when given, otherwise the preset's partitions."""
    if partitions.custom:
        return tuple(
            TableEntry(p.name, p.type, p.subtype, p.size, p.loc) for p in partitions.custom
        )
    if partitions.preset is not None and partitions.preset in data.presets:
        return tuple(
            TableEntry(p.name, p.type, p.subtype, p.size, partitions.loc)
            for p in data.presets[partitions.preset]
        )
    return ()


def _align(value: int, alignment: int) -> int:
    return -(-value // alignment) * alignment


def layout(table: tuple[TableEntry, ...], data: PartitionData, flash_size: int) -> list[Placed]:
    """Place ``table`` after the partition table; ``rest`` runs to the end of flash."""
    offset = data.table_offset + data.table_size
    placed: list[Placed] = []
    for entry in table:
        alignment = data.app_align if entry.type == "app" else data.sector_size
        offset = _align(offset, alignment)
        size = max(flash_size - offset, 0) if entry.size == REST else parse_size(entry.size)
        placed.append(Placed(entry, offset, size))
        offset += size
    return placed
