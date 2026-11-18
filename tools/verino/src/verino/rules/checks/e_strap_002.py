"""E-STRAP-002: the connection forces a error-level strapping pin away from its safe boot level."""

from collections.abc import Iterator

from verino.rules.checks._strap import conflicts, describe_level, imposed_level, strap_uses
from verino.rules.context import Context, Hit
from verino.rules.registry import rule


@rule("E-STRAP-002")
def check(ctx: Context) -> Iterator[Hit]:
    for use, _info, strap in strap_uses(ctx):
        level = imposed_level(ctx, use)
        if strap.severity == "error" and conflicts(level, strap.boot_safe):
            yield use.hit(
                f"{use.pin} is a strapping pin ({strap.function}) and {use.describe()} "
                f"{describe_level(level)} at power-up",
                f"It must be {strap.boot_safe.upper()} at reset. {strap.on_violation} "
                f"({strap.ref})",
                "move this connection to a non-strapping GPIO.",
            )
