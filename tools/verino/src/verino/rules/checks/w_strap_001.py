"""W-STRAP-001: a strapping pin is used and the boot-time level of the connection is unknown."""

from collections.abc import Iterator

from verino.rules.checks._strap import UNKNOWN, imposed_level, strap_uses
from verino.rules.context import Context, Hit
from verino.rules.registry import rule


@rule("W-STRAP-001")
def check(ctx: Context) -> Iterator[Hit]:
    for use, _info, strap in strap_uses(ctx):
        if strap.severity in ("error", "warning") and imposed_level(ctx, use) == UNKNOWN:
            yield use.hit(
                f"{use.pin} is a strapping pin ({strap.function}) and the level "
                f"{use.describe()} puts on it at power-up is unknown",
                f"It must be {strap.boot_safe.upper()} at reset. {strap.on_violation}",
                "use another GPIO, or make sure the circuit keeps the safe level at reset "
                "and acknowledge with `ack`.",
            )
