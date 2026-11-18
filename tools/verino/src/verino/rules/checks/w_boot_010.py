"""W-BOOT-010: an actuator sits on a pin that is not at its safe level during boot."""

from collections.abc import Iterator

from verino.rules.context import Context, Hit
from verino.rules.registry import rule

UNSAFE_GLITCH = {"low": ("high", "pull_up"), "high": ("low", "pull_down")}
UNSAFE_STATE = {"low": "pulled_high", "high": "pulled_low"}


@rule("W-BOOT-010")
def check(ctx: Context) -> Iterator[Hit]:
    chip = ctx.require_chip()
    for use in ctx.canonical_uses():
        if use.device is None:
            continue
        part = ctx.db.part(ctx.spec.devices[use.owner_id].part)
        info = chip.pin(use.pin)
        if part is None or not part.actuator or info is None or info.boot is None:
            continue
        safe = part.safe_boot_level
        if safe not in UNSAFE_STATE:
            continue
        bad_glitches = [g for g in info.boot.glitches if g in UNSAFE_GLITCH[safe]]
        if info.boot.state == UNSAFE_STATE[safe]:
            problem = f"is {info.boot.state.replace('_', ' ')} during reset"
        elif bad_glitches:
            problem = f"has {'/'.join(bad_glitches)} glitches at power-up"
        else:
            continue
        yield use.hit(
            f"actuator '{use.owner_id}' ({part.part}) is safe {safe.upper()} "
            f"but {use.pin} {problem}",
            "The actuator can switch briefly before the firmware sets the pin.",
            "use a GPIO that stays at the safe level during boot (no glitches, matching pull).",
        )
