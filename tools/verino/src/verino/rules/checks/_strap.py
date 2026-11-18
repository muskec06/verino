"""Shared helpers for boot-time (Level 2) rules."""

from collections.abc import Iterator

from verino.chipdata.db import PinInfo, Strap
from verino.rules.context import Context, PinUse

UNKNOWN = "unknown"


def imposed_level(ctx: Context, use: PinUse) -> str:
    """Level the connected circuit puts on the pin at power-up: pulled_high, pulled_low,
    none (no pull) or unknown."""
    if use.owner_kind == "bus":
        bus = ctx.spec.buses[use.owner_id]
        if bus.kind == "i2c" and bus.pullups is not None:
            return "pulled_high" if bus.pullups.startswith("external") else "none"
        return UNKNOWN
    device = ctx.spec.devices[use.owner_id]
    part = ctx.db.part(device.part)
    if part is None:
        return UNKNOWN
    level = part.reset_imposes.get(use.role, UNKNOWN)
    return level if level in ("pulled_high", "pulled_low", "none") else UNKNOWN


def conflicts(level: str, boot_safe: str) -> bool:
    return (level == "pulled_high" and boot_safe == "low") or (
        level == "pulled_low" and boot_safe == "high"
    )


def strap_uses(ctx: Context) -> Iterator[tuple[PinUse, PinInfo, Strap]]:
    chip = ctx.require_chip()
    for use in ctx.canonical_uses():
        info = chip.pin(use.pin)
        if info is not None and info.strap is not None:
            yield use, info, info.strap


def describe_level(level: str) -> str:
    return {"pulled_high": "pulls it HIGH", "pulled_low": "pulls it LOW"}.get(level, level)
