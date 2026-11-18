"""Chip data tests: schema, provenance, TODO(verify) bookkeeping and consistency with ESP-IDF."""

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from conftest import REPO_ROOT
from jsonschema import Draft202012Validator

from verino.chipdata.extract_soc_caps import CHIPS, extract
from verino.model.yamlio import load_text

CHIPDATA = REPO_ROOT / "chipdata"
SCHEMA = json.loads((REPO_ROOT / "schemas" / "chipdata.schema.json").read_text(encoding="utf-8"))
DATA_FILES = sorted(
    [
        CHIPDATA / "sources.yaml",
        CHIPDATA / "rules" / "rules.yaml",
        *CHIPDATA.glob("chips/*.yaml"),
        *CHIPDATA.glob("modules/*.yaml"),
    ]
)
CHIP_FILES = sorted(CHIPDATA.glob("chips/*.yaml"))
MODULE_FILES = sorted(CHIPDATA.glob("modules/*.yaml"))
TODO = "TODO(verify)"


def _load(path: Path) -> Any:
    return load_text(path.read_text(encoding="utf-8"))


def _rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _walk(node: Any, path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], Any]]:
    yield path, node
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk(value, (*path, str(key)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, (*path, str(index)))


def test_schema_is_valid() -> None:
    Draft202012Validator.check_schema(SCHEMA)


def test_phase0_data_files_exist() -> None:
    names = {_rel(p) for p in DATA_FILES}
    assert {
        "chipdata/sources.yaml",
        "chipdata/chips/esp32s3.yaml",
        "chipdata/modules/esp32-s3-wroom-1-n8r8.yaml",
        "chipdata/modules/esp32-s3-wroom-1-n16r8.yaml",
    } <= names


@pytest.mark.parametrize("path", DATA_FILES, ids=_rel)
def test_file_matches_schema(path: Path) -> None:
    errors = sorted(
        f"{'/'.join(map(str, e.absolute_path))}: {e.message}"
        for e in Draft202012Validator(SCHEMA).iter_errors(_load(path))
    )
    assert errors == []


@pytest.mark.parametrize("path", [*CHIP_FILES, *MODULE_FILES], ids=_rel)
def test_every_manual_fact_has_provenance(path: Path) -> None:
    manual = _load(path).get("manual") or {}
    missing = []
    for key, group in manual.items():
        if "provenance" in group:
            continue
        entries = list(group.values()) if isinstance(group, dict) else []
        if not entries or not all(isinstance(e, dict) and "provenance" in e for e in entries):
            missing.append(key)
    assert missing == []


@pytest.mark.parametrize("path", [*CHIP_FILES, *MODULE_FILES], ids=_rel)
def test_provenance_sources_are_registered(path: Path) -> None:
    registered = set(_load(CHIPDATA / "sources.yaml")["sources"])
    cited = {
        str(node["source"])
        for _, node in _walk(_load(path))
        if isinstance(node, dict) and "source" in node and "kind" in node
    }
    assert cited
    assert cited - registered == set()


def test_every_todo_is_listed_in_the_plan() -> None:
    plan = (REPO_ROOT / "docs" / "plan" / "phase0.md").read_text(encoding="utf-8")
    listed = plan.split("## TODO(verify)", 1)[1].split("\n## ", 1)[0]
    unlisted = [
        f"{_rel(path)}:{'.'.join(p)}"
        for path in DATA_FILES
        for p, node in _walk(_load(path))
        if node == TODO and f"`{_rel(path)}` `{'.'.join(p)}`" not in listed
    ]
    assert unlisted == []


@pytest.mark.parametrize("path", CHIP_FILES, ids=_rel)
def test_manual_pins_exist_in_soc_caps(path: Path) -> None:
    doc = _load(path)
    valid = set(doc["soc_caps"]["gpio"]["valid"])
    manual = doc.get("manual") or {}
    used: set[str] = set(manual.get("strapping") or {})
    for group in manual.values():
        if isinstance(group, dict) and isinstance(group.get("pins"), dict):
            used |= set(group["pins"])
    assert used - valid == set()


@pytest.mark.parametrize("path", CHIP_FILES, ids=_rel)
def test_fixed_pins_agree_with_datasheet(path: Path) -> None:
    doc = _load(path)
    fixed = doc["soc_caps"]["fixed_pins"]
    manual = doc["manual"]
    assert {fixed["usb_dm"], fixed["usb_dp"]} == set(manual["usb_pins"]["pins"])
    uart0 = {signal: pin for pin, signal in manual["uart0_pins"]["pins"].items()}
    assert (fixed["uart0_tx"], fixed["uart0_rx"]) == (uart0["U0TXD"], uart0["U0RXD"])


@pytest.mark.parametrize("path", MODULE_FILES, ids=_rel)
def test_module_pins_exist_on_its_chip(path: Path) -> None:
    module = _load(path)
    chip = _load(CHIPDATA / "chips" / f"{module['chip']}.yaml")
    valid = set(chip["soc_caps"]["gpio"]["valid"])
    manual = module["manual"]
    assert set(manual["exposed_gpios"]["pins"]) - valid == set()
    internal = set((manual.get("internal_pins") or {}).get("pins") or {})
    assert internal <= set(manual["exposed_gpios"]["pins"]) | valid


@pytest.mark.skipif("VERINO_IDF_PATH" not in os.environ, reason="VERINO_IDF_PATH not set")
@pytest.mark.parametrize("path", CHIP_FILES, ids=_rel)
def test_soc_caps_block_matches_idf(path: Path) -> None:
    doc = _load(path)
    expected = extract(Path(os.environ["VERINO_IDF_PATH"]), CHIPS[str(doc["chip"])])
    assert json.loads(json.dumps(doc["soc_caps"])) == json.loads(json.dumps(expected))
