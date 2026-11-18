"""E-MEM-003: flash or PSRAM settings differ from the module."""

from collections.abc import Iterator

from verino.chipdata.partitions import parse_size
from verino.rules.context import Context, Hit
from verino.rules.registry import rule


def _mhz(freq: str) -> int:
    return int(freq.removesuffix("m"))


@rule("E-MEM-003")
def check(ctx: Context) -> Iterator[Hit]:
    memory, module = ctx.spec.memory, ctx.module
    if memory is None or module is None:
        return
    name = module.module
    fix_module = "use the module's value, or set 'module' to the module that is fitted."

    flash = memory.flash
    if flash is not None:
        if (
            flash.size is not None
            and module.flash_size is not None
            and parse_size(flash.size) != parse_size(module.flash_size)
        ):
            yield Hit(
                ctx.loc("memory", "flash", "size"),
                "memory.flash.size",
                f"flash size {flash.size} differs from module '{name}' ({module.flash_size})",
                "Images built for the wrong flash size fail to boot or waste flash.",
                fix_module,
            )
        if (
            flash.freq is not None
            and module.flash_max_freq_mhz is not None
            and _mhz(flash.freq) > module.flash_max_freq_mhz
        ):
            yield Hit(
                ctx.loc("memory", "flash", "freq"),
                "memory.flash.freq",
                f"flash frequency {flash.freq} exceeds module '{name}' "
                f"({module.flash_max_freq_mhz} MHz max)",
                "Running flash above its rated frequency causes read errors and crashes.",
                f"use {module.flash_max_freq_mhz}m or less.",
            )

    psram = memory.psram
    if psram is None:
        return
    if module.psram_size is None:
        yield Hit(
            ctx.key_loc("memory", "psram"),
            "memory.psram",
            f"PSRAM is configured but module '{name}' has none",
            "Enabling PSRAM on a module without it makes start-up fail.",
            "remove memory.psram, or set 'module' to a variant with PSRAM.",
        )
        return
    if psram.size is not None and parse_size(psram.size) != parse_size(module.psram_size):
        yield Hit(
            ctx.loc("memory", "psram", "size"),
            "memory.psram.size",
            f"PSRAM size {psram.size} differs from module '{name}' ({module.psram_size})",
            "The firmware would assume PSRAM that is not there, or ignore PSRAM that is.",
            fix_module,
        )
    if psram.mode is not None and psram.mode != module.psram_interface:
        yield Hit(
            ctx.loc("memory", "psram", "mode"),
            "memory.psram.mode",
            f"PSRAM mode {psram.mode} differs from module '{name}' ({module.psram_interface})",
            "PSRAM initialisation fails when the configured mode does not match the chip.",
            fix_module,
        )
