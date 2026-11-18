"""E-REF-001: no chip data for the module or its chip."""

from collections.abc import Iterator

from verino.rules.context import Context, Hit
from verino.rules.registry import rule


@rule("E-REF-001", needs_chip=False)
def check(ctx: Context) -> Iterator[Hit]:
    module = ctx.spec.module
    if ctx.module is None:
        known = ", ".join(ctx.db.modules()) or "none"
        yield Hit(
            ctx.loc("module"),
            "module",
            f"no chip data for module '{module}'",
            "Pin, memory and boot rules need the module and chip data; none of them can run.",
            f"use a supported module ({known}) or add chipdata/modules/{module}.yaml.",
        )
    elif ctx.chip is None:
        yield Hit(
            ctx.loc("module"),
            "module",
            f"module '{module}' refers to chip '{ctx.module.chip}', which has no chip data",
            "Pin, memory and boot rules need the chip data; none of them can run.",
            f"add chipdata/chips/{ctx.module.chip}.yaml.",
        )
