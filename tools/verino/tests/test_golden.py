"""Golden files: check reports and rendered outputs must stay byte-identical.

Regenerate after an intended change with ``pytest tests/test_golden.py --update-golden``
and review the diff. The package version is stored as ``{VERSION}``.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import REPO_ROOT, VALID_EXAMPLES

from verino import __version__
from verino.chipdata.db import ChipDB
from verino.model import load_hardware
from verino.render import PINS_HPP, SDKCONFIG, render_file
from verino.report import to_json, to_text
from verino.rules import check

GOLDEN = Path(__file__).parent / "golden"
DB = ChipDB(REPO_ROOT / "chipdata")
RENDERED = ["s3-datalogger", "s3-minimal"]


def _rel(path: Path) -> Path:
    return path.relative_to(REPO_ROOT)


def _compare(request: pytest.FixtureRequest, golden: Path, text: str) -> None:
    text = text.replace(__version__, "{VERSION}")
    if request.config.getoption("--update-golden"):
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(text, encoding="utf-8", newline="\n")
    assert golden.is_file(), f"missing {golden}; run pytest --update-golden"
    assert text == golden.read_text(encoding="utf-8"), f"{golden} differs"


@pytest.mark.parametrize("path", VALID_EXAMPLES, ids=lambda p: p.stem)
def test_check_report(
    path: Path, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    report = check(load_hardware(_rel(path)), DB)
    _compare(request, GOLDEN / path.stem / "check.txt", to_text(report))
    _compare(request, GOLDEN / path.stem / "check.json", to_json(report))


@pytest.mark.parametrize("stem", RENDERED)
def test_render_outputs(stem: str, request: pytest.FixtureRequest) -> None:
    result = render_file(REPO_ROOT / "examples" / "hw" / f"{stem}.yaml", DB)
    assert result.files, result.reason
    for rel, text in result.files.items():
        _compare(request, GOLDEN / stem / rel, text)
    expected = {p.relative_to(GOLDEN / stem).as_posix() for p in (GOLDEN / stem / "gen").rglob("*")}
    assert set(result.files) == expected


def test_examples_with_errors_are_not_rendered() -> None:
    result = render_file(REPO_ROOT / "examples" / "hw" / "s3-greenhouse.yaml", DB)
    assert result.files == {}
    assert result.report.status == "error"


@pytest.mark.skipif(shutil.which("g++") is None, reason="g++ not installed")
@pytest.mark.parametrize("stem", RENDERED)
def test_pins_hpp_compiles_standalone(stem: str, tmp_path: Path) -> None:
    header = render_file(REPO_ROOT / "examples" / "hw" / f"{stem}.yaml", DB).files[PINS_HPP]
    (tmp_path / "pins.hpp").write_text(header, encoding="utf-8")
    source = tmp_path / "main.cpp"
    source.write_text(
        '#include "pins.hpp"\n'
        'static_assert(pins::i2c0::SDA >= 0, "pin");\n'
        "int main() { return 0; }\n",
        encoding="utf-8",
    )
    subprocess.run(
        ["g++", "-std=c++17", "-Wall", "-Werror", "-fsyntax-only", str(source)],
        check=True,
        capture_output=True,
    )


def _kconfig_symbols(idf: Path, chip: str) -> set[str]:
    """``config``/``choice`` names in Kconfig files that apply to ``chip``."""
    symbols: set[str] = set()
    for path in (idf / "components").rglob("Kconfig*"):
        parts = path.relative_to(idf).parts
        if any(p.startswith("esp32") and p != chip for p in parts):
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            words = line.split()
            if len(words) >= 2 and words[0] in ("config", "menuconfig", "choice"):
                symbols.add(words[1])
    return symbols


@pytest.mark.skipif("VERINO_IDF_PATH" not in os.environ, reason="VERINO_IDF_PATH not set")
@pytest.mark.parametrize("stem", RENDERED)
def test_sdkconfig_symbols_exist_in_idf(stem: str) -> None:
    result = render_file(REPO_ROOT / "examples" / "hw" / f"{stem}.yaml", DB)
    used = {
        line.split("=", 1)[0].removeprefix("CONFIG_")
        for line in result.files[SDKCONFIG].splitlines()
        if line.startswith("CONFIG_")
    }
    known = _kconfig_symbols(Path(os.environ["VERINO_IDF_PATH"]), "esp32s3")
    assert used - known == set()
