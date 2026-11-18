"""E-VOLT-001: a part drives a pin above the chip's IO voltage limit."""

from collections.abc import Iterator

from verino.rules.context import Context, Hit
from verino.rules.registry import rule


@rule("E-VOLT-001")
def check(ctx: Context) -> Iterator[Hit]:
    chip = ctx.require_chip()
    limit = chip.io_input_max_volts
    if limit is None:
        return
    for use in ctx.canonical_uses():
        if use.device is None:
            continue
        part = ctx.db.part(ctx.spec.devices[use.owner_id].part)
        if part is None or part.supply is None:
            continue
        pin = part.pins.get(use.role)
        if pin is None or pin.level not in ("supply", "pullup"):
            continue
        lowest = part.supply[0]
        if lowest > limit:
            source = " (community source)" if part.supply_kind == "community" else ""
            yield use.hit(
                f"{part.part} {use.role} drives {lowest:g} V or more into {use.pin}{source}",
                f"{chip.chip} pins accept at most {limit:g} V; a direct connection can damage it.",
                "add a voltage divider or a level shifter, or use a 3.3 V part.",
            )
