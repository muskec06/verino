"""W-ADC-003: ADC2 pin while Wi-Fi is on, on a chip where ADC2 is shared with Wi-Fi."""

from collections.abc import Iterator

from verino.rules.context import Context, Hit
from verino.rules.registry import rule


@rule("W-ADC-003")
def check(ctx: Context) -> Iterator[Hit]:
    chip = ctx.require_chip()
    if chip.adc2_wifi != "shared" or not ctx.spec.uses_wifi:
        return
    adc1 = [p.name for p in chip.pins.values() if p.adc is not None and p.adc[0] == "adc1"]
    assumed = "" if ctx.spec.uses is not None else " (`uses` is missing, so Wi-Fi is assumed)"
    for use in ctx.canonical_uses():
        device = ctx.spec.devices.get(use.owner_id) if use.device else None
        info = chip.pin(use.pin)
        if device is not None and device.kind == "adc" and info is not None and info.adc:
            unit, channel = info.adc
            if unit == "adc2":
                yield use.hit(
                    f"{use.pin} is ADC2 channel {channel} and Wi-Fi is on{assumed}",
                    f"On {chip.chip} Wi-Fi also uses ADC2; reads can fail while Wi-Fi holds it.",
                    f"use an ADC1 pin ({', '.join(adc1)}), or set `uses` without wifi.",
                )
