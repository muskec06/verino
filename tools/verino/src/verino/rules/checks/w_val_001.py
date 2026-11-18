"""W-VAL-001: the ``validation`` checksum does not match the file."""

from collections.abc import Iterator

from verino.model.checksum import content_checksum
from verino.rules.context import Context, Hit
from verino.rules.registry import rule


@rule("W-VAL-001", needs_chip=False)
def check(ctx: Context) -> Iterator[Hit]:
    validation = ctx.spec.validation
    if validation is None or validation.checksum == content_checksum(ctx.document):
        return
    yield Hit(
        ctx.key_loc("validation"),
        "validation",
        f"validation block (status '{validation.status}') was written for a different "
        "version of this file",
        "The file changed after it was last validated, so the recorded status may be wrong.",
        "run `verino pins check --write` to validate the file again.",
    )
