"""I-STRAP-004: a strapping pin whose boot function is informational is used."""

from collections.abc import Iterator

from verino.rules.checks._strap import strap_uses
from verino.rules.context import Context, Hit
from verino.rules.registry import rule


@rule("I-STRAP-004")
def check(ctx: Context) -> Iterator[Hit]:
    for use, _info, strap in strap_uses(ctx):
        if strap.severity == "info":
            yield use.hit(
                f"{use.pin} is a strapping pin ({strap.function})",
                strap.on_violation,
                "nothing to do unless the eFuse condition applies; then keep the level defined.",
            )
