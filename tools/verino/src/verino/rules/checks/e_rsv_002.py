"""E-RSV-002: USB D-/D+ pin."""

from collections.abc import Iterator

from verino.rules.checks._groups import group_hits
from verino.rules.context import Context, Hit
from verino.rules.registry import rule


@rule("E-RSV-002")
def check(ctx: Context) -> Iterator[Hit]:
    yield from group_hits(
        ctx,
        "usb_pins",
        "a USB pin",
        "It is connected to the USB Serial/JTAG controller by default; using it as GPIO "
        "disables USB flashing and the USB console.",
        "use another GPIO, or acknowledge with `ack` if USB is not used.",
    )
