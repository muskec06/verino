"""Shared helper for rules about reserved pin groups."""

from collections.abc import Iterator

from verino.rules.context import Context, Hit


def group_hits(ctx: Context, group: str, label: str, why: str, fix: str) -> Iterator[Hit]:
    chip = ctx.require_chip()
    for use in ctx.canonical_uses():
        info = chip.pin(use.pin)
        if info is not None and group in info.groups:
            yield use.hit(f"{use.pin} is {label} ({info.groups[group]})", why, fix)
