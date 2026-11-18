"""``verino pins check``: output, exit codes, checksum and ``--write``."""

import json
import shutil
from pathlib import Path

from conftest import REPO_ROOT
from typer.testing import CliRunner

from verino.chipdata.db import ChipDB
from verino.cli import app
from verino.model import load_hardware
from verino.model.checksum import content_checksum
from verino.model.yamlio import load_text
from verino.report import reserved_pins, to_dict, write_back
from verino.rules import check

EXAMPLES = REPO_ROOT / "examples" / "hw"
FIXTURES = REPO_ROOT / "chipdata" / "rules" / "fixtures"
DB = ChipDB(REPO_ROOT / "chipdata")
runner = CliRunner()


def _copy(src: Path, tmp_path: Path) -> Path:
    dst = tmp_path / src.name
    shutil.copyfile(src, dst)
    return dst


def test_checksum_ignores_comments_order_and_tool_blocks() -> None:
    base = content_checksum(load_text("schema: verino-hw/1\nmodule: m\n"))
    assert content_checksum(load_text("# note\nmodule: m  # x\nschema: verino-hw/1\n")) == base
    assert content_checksum(load_text("schema: verino-hw/1\nmodule: m\nreserved: []\n")) == base
    assert content_checksum(load_text("schema: verino-hw/1\nmodule: n\n")) != base


def test_reserved_pins_for_octal_psram_module() -> None:
    module = DB.module("esp32-s3-wroom-1-n16r8")
    assert module is not None
    chip = DB.chip(module.chip)
    assert chip is not None
    pairs = {why: pins for pins, why in reserved_pins(chip, module)}
    assert pairs["flash"] == [f"GPIO{n}" for n in range(26, 33)]
    assert pairs["octal_psram"] == [f"GPIO{n}" for n in range(33, 38)]
    assert pairs["usb"] == ["GPIO19", "GPIO20"]
    assert pairs["uart0_console"] == ["GPIO43", "GPIO44"]


def test_write_keeps_user_content_and_is_idempotent(tmp_path: Path) -> None:
    path = _copy(EXAMPLES / "s3-minimal.yaml", tmp_path)
    before = path.read_text(encoding="utf-8")
    outcome = write_back(path, DB)
    assert outcome.written
    after = path.read_text(encoding="utf-8")
    assert after.startswith(before.rstrip("\n"))
    doc = load_text(after)
    assert doc["validation"]["status"] == outcome.report.status == "warnings"
    assert list(doc["validation"]["warnings"]) == ["W-REF-002"]
    assert doc["validation"]["chipdata"] == "esp32s3@" + DB.version()
    assert doc["validation"]["checksum"] == content_checksum(doc)
    assert "W-VAL-001" not in outcome.report.ids()
    write_back(path, DB)
    assert path.read_text(encoding="utf-8") == after


def test_edit_after_write_makes_validation_stale(tmp_path: Path) -> None:
    path = _copy(EXAMPLES / "s3-minimal.yaml", tmp_path)
    write_back(path, DB)
    path.write_text(path.read_text(encoding="utf-8").replace("0x77", "0x76"), encoding="utf-8")
    assert "W-VAL-001" in check(load_hardware(path), DB).ids()
    assert "W-VAL-001" not in write_back(path, DB).report.ids()


def test_write_refuses_files_with_schema_errors(tmp_path: Path) -> None:
    path = tmp_path / "hw.yaml"
    path.write_text("schema: verino-hw/1\n", encoding="utf-8")
    outcome = write_back(path, DB)
    assert not outcome.written
    assert path.read_text(encoding="utf-8") == "schema: verino-hw/1\n"


def test_cli_exit_codes() -> None:
    ok = runner.invoke(app, ["pins", "check", str(FIXTURES / "E-PIN-001" / "clean.yaml")])
    warn = runner.invoke(app, ["pins", "check", str(EXAMPLES / "s3-minimal.yaml")])
    err = runner.invoke(app, ["pins", "check", str(EXAMPLES / "s3-greenhouse.yaml")])
    assert (ok.exit_code, warn.exit_code, err.exit_code) == (0, 1, 2)
    assert ok.stdout.rstrip().endswith(": ok (0 errors, 0 warnings, 0 info, 0 acknowledged)")
    assert "E-VOLT-001" in err.stdout


def test_cli_json_matches_report() -> None:
    path = EXAMPLES / "s3-greenhouse.yaml"
    result = runner.invoke(app, ["pins", "check", "--json", str(path)])
    data = json.loads(result.stdout)
    assert data["schema"] == "verino-report/1"
    assert data == to_dict(check(load_hardware(path), DB))
    assert result.exit_code == data["exit_code"] == 2


def test_cli_write(tmp_path: Path) -> None:
    path = _copy(EXAMPLES / "s3-minimal.yaml", tmp_path)
    result = runner.invoke(app, ["pins", "check", "--write", str(path)])
    assert result.exit_code == 1
    assert "validation:" in path.read_text(encoding="utf-8")


def test_cli_missing_file(tmp_path: Path) -> None:
    result = runner.invoke(app, ["pins", "check", str(tmp_path / "nope.yaml")])
    assert result.exit_code == 2
