"""Content checksum of a ``hardware.yaml`` document (``validation.checksum``).

The checksum covers the data, not the text: it is the sha256 of the canonical JSON
(sorted keys, no whitespace) of the document without the tool blocks ``reserved`` and
``validation``. Comments, key order and formatting do not change it (change note 0005).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from verino.model.yamlio import TOOL_BLOCKS


def _plain(node: Any) -> Any:
    if isinstance(node, Mapping):
        return {str(k): _plain(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_plain(v) for v in node]
    if isinstance(node, bool) or node is None:
        return node
    if isinstance(node, int):
        return int(node)
    if isinstance(node, float):
        return float(node)
    return str(node)


def content_checksum(document: Any) -> str:
    """``sha256:<hex>`` of the user data in ``document`` (a parsed ``hardware.yaml``)."""
    data = {k: v for k, v in _plain(document).items() if k not in TOOL_BLOCKS}
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
