"""E-RSV-001: the pin is used by flash or PSRAM."""

from collections.abc import Iterator

from verino.rules.context import Context, Hit
from verino.rules.registry import rule

FIX = "use another GPIO; these pins are taken by the memory."


@rule("E-RSV-001")
def check(ctx: Context) -> Iterator[Hit]:
    chip = ctx.require_chip()
    module = ctx.module
    for use in ctx.canonical_uses():
        info = chip.pin(use.pin)
        if module is not None and use.pin in module.internal:
            yield use.hit(
                f"{use.pin} is used inside {module.part_number} ({module.internal[use.pin]})",
                "The module wires this pad to its memory; driving it corrupts flash/PSRAM.",
                FIX,
            )
        elif info is not None and "spi_flash_pins" in info.groups:
            yield use.hit(
                f"{use.pin} is a flash/PSRAM SPI pin ({info.groups['spi_flash_pins']})",
                "SPI0/1 reach the flash and PSRAM through these pins; using them stops execution.",
                FIX,
            )
