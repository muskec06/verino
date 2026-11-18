"""E-ADC-001: analog input on a pin without an ADC channel."""

from collections.abc import Iterator

from verino.rules.context import Context, Hit
from verino.rules.registry import rule


@rule("E-ADC-001")
def check(ctx: Context) -> Iterator[Hit]:
    chip = ctx.require_chip()
    adc_pins = [p.name for p in chip.pins.values() if p.adc is not None]
    for use in ctx.canonical_uses():
        device = ctx.spec.devices.get(use.owner_id) if use.device else None
        info = chip.pin(use.pin)
        if device is not None and device.kind == "adc" and info is not None and info.adc is None:
            yield use.hit(
                f"{use.pin} has no ADC channel",
                f"Device '{device.id}' is an analog input; this pin cannot be sampled.",
                f"use an ADC pin ({adc_pins[0]}-{adc_pins[-1]} have ADC channels).",
            )
