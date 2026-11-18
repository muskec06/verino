"""Round-trip YAML I/O that keeps user comments, key order and formatting."""

from __future__ import annotations

import io
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

# Only these top-level blocks may be written by tools; everything else belongs to the user.
TOOL_BLOCKS = frozenset({"reserved", "validation"})


def _yaml() -> YAML:
    yaml = YAML(typ="rt")
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.preserve_quotes = True
    yaml.width = 4096
    return yaml


def load_text(text: str) -> Any:
    """Parse YAML text into ruamel round-trip objects (raises ``ruamel.yaml.YAMLError``)."""
    return _yaml().load(text)


def dump_text(doc: Any) -> str:
    """Serialize a round-trip document back to text with LF line endings."""
    buf = io.StringIO()
    _yaml().dump(doc, buf)
    return buf.getvalue()


def set_tool_block(doc: CommentedMap, key: str, value: Any) -> None:
    """Replace a tool-owned top-level block (``reserved`` or ``validation``)."""
    if key not in TOOL_BLOCKS:
        raise ValueError(
            f"'{key}' is a user field; only tool blocks {sorted(TOOL_BLOCKS)} may be written"
        )
    doc[key] = value
