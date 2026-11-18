"""E-PERIPH-001: more buses or PWM outputs than the chip provides."""

from collections.abc import Iterator

from verino.rules.context import Context, Hit
from verino.rules.registry import rule

BUS_LIMITS = {"i2c": ("SOC_I2C_NUM", "I2C controllers"), "uart": ("SOC_UART_NUM", "UARTs")}


@rule("E-PERIPH-001")
def check(ctx: Context) -> Iterator[Hit]:
    chip = ctx.require_chip()
    limits = {kind: (chip.macros[macro], label) for kind, (macro, label) in BUS_LIMITS.items()}
    limits["spi"] = (len(chip.spi_hosts), "general-purpose SPI hosts")
    seen: dict[str, int] = {}
    for bus in ctx.spec.buses.values():
        seen[bus.kind] = seen.get(bus.kind, 0) + 1
        limit, label = limits[bus.kind]
        if seen[bus.kind] > limit:
            note = " (UART0 is one of them and usually the console)" if bus.kind == "uart" else ""
            yield Hit(
                ctx.key_loc("buses", bus.id),
                f"buses.{bus.id}",
                f"{chip.chip} has {limit} {label}{note}; '{bus.id}' is number {seen[bus.kind]}",
                "There is no hardware controller left for this bus.",
                "share an existing bus between devices, or remove this one.",
            )
        if bus.kind == "spi" and bus.host is not None and bus.host not in chip.spi_hosts:
            yield Hit(
                ctx.loc("buses", bus.id, "host"),
                f"buses.{bus.id}.host",
                f"{bus.host} is not a general-purpose SPI host on {chip.chip}",
                "The other SPI controllers serve the flash and PSRAM.",
                f"use one of: {', '.join(chip.spi_hosts)}.",
            )
    channels = chip.macros["SOC_LEDC_CHANNEL_NUM"]
    pwm = [d for d in ctx.spec.devices.values() if d.kind == "pwm"]
    for index, device in enumerate(pwm[channels:], start=channels + 1):
        yield Hit(
            ctx.key_loc("devices", device.id),
            f"devices.{device.id}",
            f"{chip.chip} has {channels} LEDC channels; '{device.id}' is PWM output {index}",
            "Each PWM output needs its own LEDC channel.",
            "drive fewer PWM outputs or move some to another peripheral.",
        )
