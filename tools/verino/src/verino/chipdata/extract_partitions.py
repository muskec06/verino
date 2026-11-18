"""Extract the ESP-IDF built-in partition tables into ``chipdata/idf/partitions.yaml``.

Usage::

    python -m verino.chipdata.extract_partitions --idf <esp-idf> \
        --out chipdata/idf/partitions.yaml

Only the ``generated`` block is written; ``manual`` and comments are preserved.
Sizes are kept exactly as written in the CSV files (change note 0005).
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from pathlib import Path

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from verino.chipdata.extract_soc_caps import ExtractError, idf_commit, idf_version
from verino.model.yamlio import dump_text, load_text

GENERATOR = "verino.chipdata.extract_partitions"
TABLE_DIR = "components/partition_table"

# Built-in tables offered as presets: plain layouts without flags or TEE partitions.
PRESETS = ("singleapp", "singleapp_large", "two_ota", "two_ota_large")


def _rows(path: Path) -> list[list[str]]:
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    return [[cell.strip() for cell in row] for row in csv.reader(lines)]


def _preset(idf: Path, name: str) -> CommentedMap:
    rel = f"{TABLE_DIR}/partitions_{name}.csv"
    path = idf / rel
    if not path.is_file():
        raise ExtractError(f"{rel} not found in {idf}")
    partitions = CommentedSeq()
    for row in _rows(path):
        cells = row + [""] * (6 - len(row))
        part_name, ptype, subtype, offset, size, flags = cells[:6]
        if offset or flags:
            raise ExtractError(f"{rel}: '{part_name}' has a fixed offset or flags")
        entry = CommentedMap(
            [("name", part_name), ("type", ptype), ("subtype", subtype), ("size", size)]
        )
        entry.fa.set_flow_style()
        partitions.append(entry)
    preset = CommentedMap()
    preset["file"] = rel
    preset["partitions"] = partitions
    return preset


def extract(idf: Path) -> CommentedMap:
    """Build the ``generated`` block from the tree at ``idf``."""
    version = idf_version(idf)
    block = CommentedMap()
    block["presets"] = CommentedMap((name, _preset(idf, name)) for name in PRESETS)
    provenance = CommentedMap()
    provenance["kind"] = "soc_caps"
    provenance["source"] = f"esp-idf@{version}"
    provenance["idf_version"] = version
    commit = idf_commit(idf)
    if commit:
        provenance["commit"] = commit
    provenance["generated_by"] = GENERATOR
    block["provenance"] = provenance
    return block


def update_file(path: Path, block: CommentedMap) -> None:
    """Write ``block`` as ``generated`` into ``path``; other content is left untouched."""
    if path.is_file():
        doc = load_text(path.read_text(encoding="utf-8"))
    else:
        doc = CommentedMap()
        doc["schema"] = "verino-partitions/1"
    if "generated" in doc:
        doc["generated"] = block
    else:
        doc.insert(list(doc).index("schema") + 1, "generated", block)
    path.write_text(dump_text(doc), encoding="utf-8", newline="\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m " + GENERATOR, description=__doc__)
    parser.add_argument("--idf", type=Path, required=True, help="ESP-IDF source tree")
    parser.add_argument("--out", type=Path, required=True, help="partitions file to update")
    args = parser.parse_args(argv)
    try:
        block = extract(args.idf)
        update_file(args.out, block)
    except ExtractError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"{args.out}: {len(PRESETS)} presets from ESP-IDF {block['provenance']['idf_version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
