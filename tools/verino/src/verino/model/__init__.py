"""Typed hardware.yaml model."""

from verino.model.diagnostics import SCHEMA_ERROR, YAML_ERROR, Diagnostic
from verino.model.loader import LoadResult, load_hardware, parse_hardware
from verino.model.types import (
    Ack,
    Bus,
    Device,
    FlashConfig,
    HardwareSpec,
    Location,
    Memory,
    Partition,
    Partitions,
    PinAssignment,
    PsramConfig,
    Reserved,
    Validation,
)
from verino.model.yamlio import TOOL_BLOCKS, dump_text, load_text, set_tool_block

__all__ = [
    "SCHEMA_ERROR",
    "TOOL_BLOCKS",
    "YAML_ERROR",
    "Ack",
    "Bus",
    "Device",
    "Diagnostic",
    "FlashConfig",
    "HardwareSpec",
    "LoadResult",
    "Location",
    "Memory",
    "Partition",
    "Partitions",
    "PinAssignment",
    "PsramConfig",
    "Reserved",
    "Validation",
    "dump_text",
    "load_hardware",
    "load_text",
    "parse_hardware",
    "set_tool_block",
]
