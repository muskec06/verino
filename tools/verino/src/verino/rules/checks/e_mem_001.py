"""E-MEM-001: the partition table does not fit in flash."""

from collections.abc import Iterator

from verino.chipdata.partitions import REST, format_size
from verino.rules.checks._memory import entry_path, flash_size, placed
from verino.rules.context import Context, Hit
from verino.rules.registry import rule


@rule("E-MEM-001")
def check(ctx: Context) -> Iterator[Hit]:
    size = flash_size(ctx)
    if size is None:
        return
    for index, part in enumerate(placed(ctx)):
        empty_rest = part.entry.size == REST and part.size == 0
        if part.end <= size and not empty_rest:
            continue
        path, loc = entry_path(ctx, index)
        where = (
            "has no flash left for 'rest'"
            if empty_rest
            else f"ends at {hex(part.end)}, beyond the end of flash"
        )
        yield Hit(
            loc,
            path,
            f"partition '{part.entry.name}' at {hex(part.offset)} {where} "
            f"({format_size(size)} flash)",
            "ESP-IDF cannot build or flash a partition table that does not fit in flash.",
            f"shrink the partitions to fit {format_size(size)}, or use a module with more flash.",
        )
        return
