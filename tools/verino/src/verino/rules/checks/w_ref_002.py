"""W-REF-002: no board data; board aliases cannot be resolved."""

from collections.abc import Iterator

from verino.rules.context import Context, Hit
from verino.rules.registry import rule


@rule("W-REF-002", needs_chip=False)
def check(ctx: Context) -> Iterator[Hit]:
    board = ctx.spec.board
    if board is not None and not ctx.db.has_board(board):
        yield Hit(
            ctx.loc("board"),
            "board",
            f"no board data for '{board}'",
            "Board aliases, on-board parts and defaults are unknown, so they are not checked.",
            "use canonical GPIO names, or add chipdata/boards/" + board + ".yaml.",
        )
