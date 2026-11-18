"""E-MEM-002: OTA partitions are present but the OTA layout is incomplete."""

import re
from collections.abc import Iterator

from verino.rules.checks._memory import table
from verino.rules.context import Context, Hit
from verino.rules.registry import rule

_OTA_APP = re.compile(r"^ota_[0-9]+$")


@rule("E-MEM-002")
def check(ctx: Context) -> Iterator[Hit]:
    rows = table(ctx)
    ota = ctx.db.partitions()
    apps = {e.subtype for e in rows if e.type == "app"}
    data = {e.subtype for e in rows if e.type == "data"}
    if not any(_OTA_APP.match(s) for s in apps) and ota.ota_data_subtype not in data:
        return
    missing = [f"app '{s}'" for s in ota.ota_app_subtypes if s not in apps]
    if ota.ota_data_subtype not in data:
        missing.append(f"data '{ota.ota_data_subtype}' (otadata)")
    if not missing:
        return
    yield Hit(
        ctx.key_loc("memory", "partitions"),
        "memory.partitions",
        f"OTA partition table lacks {', '.join(missing)}",
        "ESP-IDF OTA needs two OTA app slots and an OTA data partition; "
        "without them an update cannot be written or selected.",
        "add the missing partitions, or use the 'two_ota' preset.",
    )
