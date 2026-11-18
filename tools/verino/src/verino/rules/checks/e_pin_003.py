"""E-PIN-003: the same pin is assigned more than once."""

from collections.abc import Iterator

from verino.rules.context import Context, Hit, PinUse
from verino.rules.registry import rule


@rule("E-PIN-003", needs_chip=False)
def check(ctx: Context) -> Iterator[Hit]:
    first: dict[str, PinUse] = {}
    for use in ctx.pin_uses():
        earlier = first.setdefault(use.pin, use)
        if earlier is not use:
            yield use.hit(
                f"{use.pin} is already used by {earlier.describe()}",
                "Two signals on one pin short each other or make both unusable.",
                "assign a different free pin to one of them.",
            )
