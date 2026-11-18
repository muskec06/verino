"""Round-trip tests: user formatting and comments survive tool writes."""

from pathlib import Path

import pytest
from conftest import EXAMPLES, VALID_EXAMPLES

from verino.model import dump_text, load_hardware, load_text, parse_hardware, set_tool_block

GREENHOUSE = EXAMPLES / "s3-greenhouse.yaml"


@pytest.mark.parametrize("path", VALID_EXAMPLES, ids=lambda p: p.name)
def test_unmodified_round_trip_is_byte_identical(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert dump_text(load_text(text)) == text


def test_writing_validation_keeps_comments_and_order() -> None:
    text = GREENHOUSE.read_text(encoding="utf-8")
    doc = load_text(text)
    set_tool_block(
        doc,
        "validation",
        {
            "tool": "verino 0.1.0",
            "chipdata": "test",
            "status": "ok",
            "warnings": [],
            "checksum": "sha256:" + "0" * 64,
        },
    )
    out = dump_text(doc)
    assert out.startswith(text.rstrip("\n"))
    for line in text.splitlines():
        if "#" in line:
            assert line in out
    assert list(load_text(out)) == [*list(load_text(text)), "validation"]
    reloaded = parse_hardware(out, "hw.yaml")
    original = load_hardware(GREENHOUSE)
    assert reloaded.spec is not None and original.spec is not None
    assert reloaded.spec.validation is not None
    assert reloaded.spec.devices.keys() == original.spec.devices.keys()


def test_replacing_a_tool_block_is_idempotent() -> None:
    doc = load_text(GREENHOUSE.read_text(encoding="utf-8"))
    block = [{"pins": ["GPIO19", "GPIO20"], "why": "test"}]
    set_tool_block(doc, "reserved", block)
    once = dump_text(doc)
    set_tool_block(doc, "reserved", block)
    assert dump_text(doc) == once


@pytest.mark.parametrize("key", ["devices", "buses", "board", "ack", "unknown"])
def test_tools_cannot_write_user_fields(key: str) -> None:
    doc = load_text(GREENHOUSE.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="only tool blocks"):
        set_tool_block(doc, key, {})
