"""``verino pins solve``: ten scenarios with golden output, plus solver properties."""

import json
import shutil
from pathlib import Path

import pytest
from conftest import REPO_ROOT
from typer.testing import CliRunner

from verino import __version__
from verino.chipdata.db import ChipDB
from verino.cli import app
from verino.model import load_hardware, parse_hardware
from verino.render import render_file
from verino.rules import check
from verino.solve import solve
from verino.solve.output import solve_file, to_text

SCENARIOS = Path(__file__).parent / "solve"
NAMES = sorted(p.name for p in SCENARIOS.iterdir() if p.is_dir())
DB = ChipDB(REPO_ROOT / "chipdata")
runner = CliRunner()


def _locked(path: Path) -> dict[str, str]:
    spec = load_hardware(path).spec
    assert spec is not None
    owners = [*spec.buses.values(), *spec.devices.values()]
    return {f"{o.id}.{r}": a.pin for o in owners for r, a in o.pins.items() if a.locked}


def _run(name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str, int]:
    work = tmp_path / name
    work.mkdir()
    shutil.copyfile(SCENARIOS / name / "input.yaml", work / "input.yaml")
    monkeypatch.chdir(work)
    result = solve_file(Path("input.yaml"), DB, write=True, reassign="reassign" in name)
    return work / "input.yaml", to_text(result), result.exit_code


def _compare(request: pytest.FixtureRequest, golden: Path, text: str) -> None:
    text = text.replace(__version__, "{VERSION}")
    if request.config.getoption("--update-golden"):
        golden.write_text(text, encoding="utf-8", newline="\n")
    assert golden.is_file(), f"missing {golden}; run pytest --update-golden"
    assert text == golden.read_text(encoding="utf-8"), f"{golden} differs"


def test_there_are_ten_scenarios() -> None:
    assert len(NAMES) >= 10


@pytest.mark.parametrize("name", NAMES)
def test_scenario(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    locked_before = _locked(SCENARIOS / name / "input.yaml")
    path, text, code = _run(name, tmp_path, monkeypatch)
    _compare(request, SCENARIOS / name / "expected.txt", text)
    if "unsatisfiable" in name:
        assert code == 2
        assert path.read_text(encoding="utf-8") == (SCENARIOS / name / "input.yaml").read_text(
            encoding="utf-8"
        )
        return
    assert code == 0
    _compare(request, SCENARIOS / name / "solved.yaml", path.read_text(encoding="utf-8"))
    report = check(load_hardware(path), DB)
    assert report.status != "error", [str(f) for f in report.findings]
    assert _locked(path) == locked_before


@pytest.mark.parametrize("name", [n for n in NAMES if "unsatisfiable" not in n])
def test_solving_twice_changes_nothing(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _, _ = _run(name, tmp_path, monkeypatch)
    first = path.read_text(encoding="utf-8")
    again = solve_file(path, DB, write=True)
    assert again.status == "nothing_to_do"
    assert path.read_text(encoding="utf-8") == first


def test_solver_is_deterministic() -> None:
    first = solve_file(SCENARIOS / "08-full-project" / "input.yaml", DB)
    second = solve_file(SCENARIOS / "08-full-project" / "input.yaml", DB)
    assert [(a.slot.path, a.pin) for a in first.assignments] == [
        (a.slot.path, a.pin) for a in second.assignments
    ]


def test_refuses_files_with_other_errors() -> None:
    text = (
        "schema: verino-hw/1\nmodule: esp32-s3-wroom-1-n8r8\nuses: []\n"
        "devices:\n  a: {part: x, kind: gpio, pin: GPIO26}\n  b: {part: y, kind: gpio, pin: auto}\n"
    )
    result = solve(parse_hardware(text, "hw.yaml"), DB)
    assert result.status == "refused"
    assert any("E-RSV-001" in m for m in result.messages)


def test_cli_solve_json_and_exit_codes(tmp_path: Path) -> None:
    ok = runner.invoke(
        app, ["pins", "solve", "--json", str(SCENARIOS / "02-spi-iomux" / "input.yaml")]
    )
    data = json.loads(ok.stdout)
    assert ok.exit_code == 0 and data["schema"] == "verino-solve/1"
    assert [a["pin"] for a in data["assignments"]] == ["GPIO12", "GPIO11", "GPIO13", "GPIO10"]
    bad = runner.invoke(app, ["pins", "solve", str(SCENARIOS / "10-unsatisfiable" / "input.yaml")])
    assert bad.exit_code == 2
    assert "E-VOLT-001" in bad.stdout


def test_auto_pins_block_render() -> None:
    result = render_file(SCENARIOS / "01-i2c-sensor" / "input.yaml", DB)
    assert result.files == {}
    assert "E-PIN-005" in result.report.ids()
