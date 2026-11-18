"""W-RSV-003: UART0 console pin."""

from collections.abc import Iterator

from verino.rules.checks._groups import group_hits
from verino.rules.context import Context, Hit
from verino.rules.registry import rule


@rule("W-RSV-003")
def check(ctx: Context) -> Iterator[Hit]:
    yield from group_hits(
        ctx,
        "uart0_pins",
        "a UART0 pin",
        "UART0 is the default console and serial download interface; other traffic on it "
        "garbles logs and can block flashing.",
        "use another GPIO, or acknowledge with `ack` if the console is moved or disabled.",
    )
