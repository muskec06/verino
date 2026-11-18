"""W-RSV-004: JTAG pin."""

from collections.abc import Iterator

from verino.rules.checks._groups import group_hits
from verino.rules.context import Context, Hit
from verino.rules.registry import rule


@rule("W-RSV-004")
def check(ctx: Context) -> Iterator[Hit]:
    yield from group_hits(
        ctx,
        "jtag_pins",
        "a JTAG pin",
        "Using it as GPIO rules out pad JTAG debugging.",
        "use another GPIO, or acknowledge with `ack` if pad JTAG is not needed.",
    )
