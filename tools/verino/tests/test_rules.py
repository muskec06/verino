"""Rule catalog and fixtures: each rule triggers on its trigger fixture, never on its clean one."""

from pathlib import Path

import pytest
from conftest import REPO_ROOT, VALID_EXAMPLES

from verino.chipdata.db import ChipDB
from verino.model import load_hardware, parse_hardware
from verino.rules import check
from verino.rules.catalog import load_catalog
from verino.rules.registry import BUILTIN_IDS, registered

CHIPDATA = REPO_ROOT / "chipdata"
FIXTURES = CHIPDATA / "rules" / "fixtures"
DB = ChipDB(CHIPDATA)
CATALOG = load_catalog(CHIPDATA)
PREFIX = {"error": "E", "warning": "W", "info": "I"}


def _marked_lines(path: Path, rule_id: str) -> list[int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [n for n, line in enumerate(lines, start=1) if line.rstrip().endswith(f"# <- {rule_id}")]


def test_catalog_matches_implementation() -> None:
    assert set(CATALOG) == set(registered()) | BUILTIN_IDS


@pytest.mark.parametrize("rule_id", sorted(CATALOG))
def test_id_prefix_matches_severity(rule_id: str) -> None:
    assert rule_id.startswith(PREFIX[CATALOG[rule_id].severity] + "-")


@pytest.mark.parametrize("rule_id", sorted(CATALOG))
def test_rule_has_both_fixtures(rule_id: str) -> None:
    assert (FIXTURES / rule_id / "trigger.yaml").is_file()
    assert (FIXTURES / rule_id / "clean.yaml").is_file()


def test_no_fixtures_for_unknown_rules() -> None:
    assert {p.name for p in FIXTURES.iterdir() if p.is_dir()} <= set(CATALOG)


@pytest.mark.parametrize("rule_id", sorted(CATALOG))
def test_trigger_fixture(rule_id: str) -> None:
    path = FIXTURES / rule_id / "trigger.yaml"
    marked = _marked_lines(path, rule_id)
    assert marked, f"{path} has no '# <- {rule_id}' marker"
    report = check(load_hardware(path), DB)
    lines = [f.diagnostic.loc.line for f in report.findings if f.rule_id == rule_id]
    assert lines, [str(f) for f in report.findings]
    assert set(lines) & set(marked), (lines, marked)


@pytest.mark.parametrize("rule_id", sorted(CATALOG))
def test_clean_fixture(rule_id: str) -> None:
    report = check(load_hardware(FIXTURES / rule_id / "clean.yaml"), DB)
    assert rule_id not in report.ids(), [str(f) for f in report.findings]


def test_acknowledged_finding_is_reported_but_not_active() -> None:
    report = check(load_hardware(FIXTURES / "I-ACK-001" / "clean.yaml"), DB)
    acked = [f for f in report.findings if f.acknowledged]
    assert [f.rule_id for f in acked] == ["W-RSV-003"]
    assert acked[0].ack_reason == "fixture"
    assert "[acknowledged: fixture]" in str(acked[0])
    assert "W-RSV-003" not in report.ids(include_acknowledged=False)
    assert report.status == "ok"
    assert report.exit_code == 0


def test_status_and_exit_codes() -> None:
    warn = check(load_hardware(FIXTURES / "W-RSV-003" / "trigger.yaml"), DB)
    assert (warn.status, warn.exit_code) == ("warnings", 1)
    err = check(load_hardware(FIXTURES / "E-PIN-001" / "trigger.yaml"), DB)
    assert (err.status, err.exit_code) == ("error", 2)


def test_messages_follow_the_format() -> None:
    report = check(load_hardware(FIXTURES / "E-RSV-002" / "trigger.yaml"), DB)
    text = str(next(f for f in report.findings if f.rule_id == "E-RSV-002"))
    assert text.startswith("E-RSV-002 ")
    assert "GPIO19" in text
    assert "Fix:" in text


def test_loader_errors_pass_through() -> None:
    report = check(parse_hardware("schema: verino-hw/1\n", "hw.yaml"), DB)
    assert report.ids() == ["E-SCHEMA-001"]


@pytest.mark.parametrize("path", VALID_EXAMPLES, ids=lambda p: p.name)
def test_examples_run_deterministically(path: Path) -> None:
    first = [str(f) for f in check(load_hardware(path), DB).findings]
    assert [str(f) for f in check(load_hardware(path), DB).findings] == first
