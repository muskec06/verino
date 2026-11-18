"""Schema tests: the schema itself, valid examples and invalid examples."""

from pathlib import Path

import pytest
from conftest import INVALID_EXAMPLES, VALID_EXAMPLES
from jsonschema import Draft202012Validator

from verino.model import load_hardware, parse_hardware
from verino.model.schema import load_schema

# file name -> (expected line, expected column, substring of the rendered message)
INVALID_EXPECTED: dict[str, tuple[int, int, str]] = {
    "missing-origin.yaml": (8, 10, "buses.i2c0.sda: missing required field 'origin'"),
    "bad-pin-name.yaml": (6, 50, "'GPIO04' is not a valid pin name"),
    "ack-without-reason.yaml": (6, 5, "ack[0]: missing required field 'reason'"),
    "unknown-bus-ref.yaml": (12, 27, "bus 'spi2', which is not defined"),
}


def test_schema_is_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(load_schema())


def test_example_counts() -> None:
    assert len(VALID_EXAMPLES) >= 3
    assert len(INVALID_EXAMPLES) >= 3
    assert {p.name for p in INVALID_EXAMPLES} == set(INVALID_EXPECTED)


@pytest.mark.parametrize("path", VALID_EXAMPLES, ids=lambda p: p.name)
def test_valid_example_has_no_diagnostics(path: Path) -> None:
    result = load_hardware(path)
    assert [str(d) for d in result.diagnostics] == []
    assert result.spec is not None


@pytest.mark.parametrize("path", INVALID_EXAMPLES, ids=lambda p: p.name)
def test_invalid_example_reports_line_and_message(path: Path) -> None:
    line, col, text = INVALID_EXPECTED[path.name]
    result = load_hardware(path)
    assert result.spec is None
    assert len(result.diagnostics) == 1
    diag = result.diagnostics[0]
    assert diag.rule_id == "E-SCHEMA-001"
    assert (diag.loc.line, diag.loc.col) == (line, col)
    rendered = str(diag)
    assert rendered.startswith(f"E-SCHEMA-001 {path.as_posix()}:{line}:{col} ")
    assert text in rendered
    assert "Fix:" in rendered


def test_unknown_field_points_at_the_key() -> None:
    text = "schema: verino-hw/1\nmodule: m\nbaord: x\n"
    result = parse_hardware(text, "hw.yaml")
    assert [str(d) for d in result.diagnostics] == [
        "E-SCHEMA-001 hw.yaml:3:1 (root): unknown field 'baord'. Unknown fields are rejected "
        "so typos are caught. Fix: remove it or check the spelling."
    ]


def test_wrong_schema_version() -> None:
    result = parse_hardware("schema: verino-hw/2\nmodule: m\n", "hw.yaml")
    assert len(result.diagnostics) == 1
    assert "schema: 'verino-hw/2' must be 'verino-hw/1'" in str(result.diagnostics[0])


def test_yaml_syntax_error_has_line() -> None:
    result = parse_hardware("schema: verino-hw/1\nmodule: [unclosed\n", "hw.yaml")
    assert result.spec is None
    assert len(result.diagnostics) == 1
    diag = result.diagnostics[0]
    assert diag.rule_id == "E-YAML-001"
    assert diag.loc.file == "hw.yaml"
    assert diag.loc.line >= 2


def test_duplicate_key_is_a_yaml_error() -> None:
    result = parse_hardware("schema: verino-hw/1\nmodule: a\nmodule: b\n", "hw.yaml")
    assert [d.rule_id for d in result.diagnostics] == ["E-YAML-001"]


def test_root_must_be_a_mapping() -> None:
    result = parse_hardware("- a\n- b\n", "hw.yaml")
    assert [d.rule_id for d in result.diagnostics] == ["E-SCHEMA-001"]
    assert result.diagnostics[0].loc.line == 1


def test_diagnostics_are_sorted_and_deterministic() -> None:
    text = (
        "schema: verino-hw/1\nmodule: m\nbuses:\n  i2c0:\n    kind: i2c\n"
        "    sda: {pin: GPIO8}\n    scl: {pin: gpio9, origin: user}\n"
    )
    first = [str(d) for d in parse_hardware(text, "hw.yaml").diagnostics]
    second = [str(d) for d in parse_hardware(text, "hw.yaml").diagnostics]
    assert first == second
    assert [d.split()[1] for d in first] == ["hw.yaml:6:10", "hw.yaml:7:16"]
