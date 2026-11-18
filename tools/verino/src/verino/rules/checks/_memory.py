"""Shared helpers for the memory rules (E-MEM-*)."""

from __future__ import annotations

from verino.chipdata.partitions import Placed, TableEntry, entries, layout, parse_size
from verino.model.schema import format_path
from verino.model.types import Location
from verino.rules.context import Context


def flash_size(ctx: Context) -> int | None:
    """Flash size in bytes: ``memory.flash.size`` if given, else the module's."""
    memory = ctx.spec.memory
    if memory is not None and memory.flash is not None and memory.flash.size is not None:
        return parse_size(memory.flash.size)
    if ctx.module is not None and ctx.module.flash_size is not None:
        return parse_size(ctx.module.flash_size)
    return None


def table(ctx: Context) -> tuple[TableEntry, ...]:
    memory = ctx.spec.memory
    if memory is None or memory.partitions is None:
        return ()
    return entries(memory.partitions, ctx.db.partitions())


def placed(ctx: Context) -> list[Placed]:
    size = flash_size(ctx)
    rows = table(ctx)
    if size is None or not rows:
        return []
    return layout(rows, ctx.db.partitions(), size)


def entry_path(ctx: Context, index: int) -> tuple[str, Location]:
    """Path and location of the ``index``-th table entry (a custom item or the preset key)."""
    memory = ctx.spec.memory
    assert memory is not None and memory.partitions is not None
    if memory.partitions.custom:
        path: list[str | int] = ["memory", "partitions", "custom", index]
        return format_path(path), ctx.loc(*path)
    return format_path(["memory", "partitions", "preset"]), ctx.loc(
        "memory", "partitions", "preset"
    )
