"""E-PIN-002: the pin is not brought out by the module."""

from collections.abc import Iterator

from verino.rules.context import Context, Hit
from verino.rules.registry import rule


@rule("E-PIN-002")
def check(ctx: Context) -> Iterator[Hit]:
    module = ctx.module
    if module is None:
        return
    for use in ctx.canonical_uses():
        if use.pin not in module.exposed:
            yield use.hit(
                f"{use.pin} is not brought out by {module.part_number}",
                "The chip has this GPIO but the module has no pad for it, so nothing can connect.",
                "use a GPIO that reaches a module pad.",
            )
