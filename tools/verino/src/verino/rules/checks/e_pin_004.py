"""E-PIN-004: a board alias cannot be resolved."""

from collections.abc import Iterator

from verino.rules.context import Context, Hit
from verino.rules.registry import rule


@rule("E-PIN-004", needs_chip=False)
def check(ctx: Context) -> Iterator[Hit]:
    board = ctx.spec.board
    for use in ctx.pin_uses():
        if use.canonical:
            continue
        reason = "no board is set" if board is None else f"there is no board data for '{board}'"
        yield use.hit(
            f"cannot resolve board alias '{use.pin}': {reason}",
            "Without the GPIO number no pin rule can check this connection.",
            "write the GPIO name (e.g. GPIO38) or set a board with board data.",
        )
