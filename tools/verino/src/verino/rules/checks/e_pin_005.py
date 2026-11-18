"""E-PIN-005: a pin is still ``auto`` (not chosen yet)."""

from collections.abc import Iterator

from verino.rules.context import Context, Hit
from verino.rules.registry import rule


@rule("E-PIN-005", needs_chip=False)
def check(ctx: Context) -> Iterator[Hit]:
    for use in ctx.auto_uses():
        yield use.hit(
            f"{use.describe()} has no pin yet ('auto')",
            "Pin rules cannot check the connection and nothing can be rendered until "
            "every pin is chosen.",
            "run `verino pins solve --write` or write the GPIO name.",
        )
