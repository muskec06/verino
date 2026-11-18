"""E-PIN-001: the pin does not exist on the chip."""

from collections.abc import Iterator

from verino.rules.context import Context, Hit
from verino.rules.registry import rule


@rule("E-PIN-001")
def check(ctx: Context) -> Iterator[Hit]:
    chip = ctx.require_chip()
    for use in ctx.pin_uses():
        if use.canonical and chip.pin(use.pin) is None:
            yield use.hit(
                f"{use.pin} does not exist on {chip.chip}",
                f"{chip.chip} has {len(chip.pins)} usable GPIOs ({chip.idf_source} soc_caps).",
                "pick a GPIO listed for the chip, e.g. with `verino pins solve`.",
            )
