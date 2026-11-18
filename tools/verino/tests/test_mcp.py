"""MCP server: the four tools over an in-process client, plus one stdio smoke test."""

import json
import shutil
import sys
from pathlib import Path
from typing import Any

import anyio
import pytest
from conftest import EXAMPLES, REPO_ROOT
from mcp import Client, StdioServerParameters
from mcp.types import CallToolResult, TextContent
from typer.testing import CliRunner

from verino import __version__
from verino.chipdata.db import ChipDB
from verino.cli import app
from verino.mcp import build_server

DB = ChipDB(REPO_ROOT / "chipdata")
GOLDEN = Path(__file__).parent / "golden"
SOLVE = Path(__file__).parent / "solve"
TOOLS = {"list_boards", "check_hw", "solve_pins", "render_hw"}
runner = CliRunner()


def _call(name: str, arguments: dict[str, Any]) -> CallToolResult:
    async def run() -> CallToolResult:
        async with Client(build_server(DB)) as client:
            return await client.call_tool(name, arguments)

    return anyio.run(run)


def _ok(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = _call(name, arguments)
    assert not result.is_error, result.content
    assert result.structured_content is not None
    return result.structured_content


def _error(name: str, arguments: dict[str, Any]) -> str:
    result = _call(name, arguments)
    assert result.is_error
    content = result.content[0]
    assert isinstance(content, TextContent)
    return content.text


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_lists_the_four_tools() -> None:
    async def run() -> set[str]:
        async with Client(build_server(DB)) as client:
            return {t.name for t in (await client.list_tools()).tools}

    assert anyio.run(run) == TOOLS


# list_boards


def test_list_boards_returns_modules_and_parts() -> None:
    data = _ok("list_boards", {})
    assert data["schema"] == "verino-boards/1"
    assert data["chipdata"] == DB.version()
    assert data["boards"] == [{"board": b} for b in DB.boards()]
    assert [m["module"] for m in data["modules"]] == DB.modules()
    n8r8 = next(m for m in data["modules"] if m["module"] == "esp32-s3-wroom-1-n8r8")
    assert n8r8 == {
        "module": "esp32-s3-wroom-1-n8r8",
        "chip": "esp32s3",
        "part_number": "ESP32-S3-WROOM-1-N8R8",
        "flash": "8MB",
        "psram": "8MB",
    }
    assert [p["part"] for p in data["parts"]] == DB.parts()


def test_list_boards_filters() -> None:
    assert _ok("list_boards", {"chip": "esp32"})["modules"] == []
    assert len(_ok("list_boards", {"chip": "esp32s3"})["modules"]) == len(DB.modules())
    data = _ok("list_boards", {"keyword": "BME"})
    assert data["modules"] == []
    assert [p["part"] for p in data["parts"]] == ["bme280"]
    assert set(data["parts"][0]["kinds"]) == {"i2c", "spi"}


# check_hw


@pytest.mark.parametrize("stem", ["s3-datalogger", "s3-greenhouse"])
def test_check_hw_matches_cli_json(stem: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(REPO_ROOT)
    rel = f"examples/hw/{stem}.yaml"
    cli = runner.invoke(app, ["pins", "check", rel, "--json"])
    assert _ok("check_hw", {"path": rel}) == json.loads(cli.stdout)


def test_check_hw_accepts_text() -> None:
    data = _ok("check_hw", {"yaml": _text(EXAMPLES / "s3-datalogger.yaml")})
    assert data["file"] == "hardware.yaml"
    assert data["status"] == "ok"


def test_check_hw_reports_yaml_errors_as_findings() -> None:
    data = _ok("check_hw", {"yaml": "schema: verino-hw/1\nmodule: [unclosed\n"})
    assert data["status"] == "error"
    assert data["findings"]


def test_check_hw_write(tmp_path: Path) -> None:
    file = tmp_path / "hardware.yaml"
    shutil.copyfile(EXAMPLES / "s3-datalogger.yaml", file)
    data = _ok("check_hw", {"path": str(file), "write": True})
    assert data["written"] is True
    assert "validation:" in _text(file)


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({}, "give either path or yaml"),
        ({"path": "a.yaml", "yaml": "x: 1"}, "give either path or yaml"),
        ({"path": "does-not-exist.yaml"}, "file not found"),
        ({"yaml": "schema: verino-hw/1\n", "write": True}, "write needs path"),
    ],
)
def test_check_hw_input_errors(arguments: dict[str, Any], message: str) -> None:
    assert message in _error("check_hw", arguments)


# solve_pins


def test_solve_pins_text_returns_solved_yaml() -> None:
    scenario = SOLVE / "08-full-project"
    data = _ok("solve_pins", {"yaml": _text(scenario / "input.yaml")})
    assert data["schema"] == "verino-solve/1"
    assert data["status"] == "solved"
    assert data["written"] is False
    assert data["yaml"] == _text(scenario / "solved.yaml")
    assert data["report"]["status"] != "error"


def test_solve_pins_path_writes_only_when_asked(tmp_path: Path) -> None:
    scenario = SOLVE / "01-i2c-sensor"
    file = tmp_path / "hardware.yaml"
    shutil.copyfile(scenario / "input.yaml", file)
    data = _ok("solve_pins", {"path": str(file)})
    assert data["written"] is False
    assert _text(file) == _text(scenario / "input.yaml")
    data = _ok("solve_pins", {"path": str(file), "write": True})
    assert data["written"] is True
    assert _text(file) == _text(scenario / "solved.yaml")


def test_solve_pins_unsatisfiable_has_no_yaml() -> None:
    data = _ok("solve_pins", {"yaml": _text(SOLVE / "10-unsatisfiable" / "input.yaml")})
    assert data["status"] == "unsatisfiable"
    assert data["yaml"] is None
    assert data["exit_code"] == 2


def test_solve_pins_write_needs_path() -> None:
    text = _text(SOLVE / "01-i2c-sensor" / "input.yaml")
    assert "write needs path" in _error("solve_pins", {"yaml": text, "write": True})


# render_hw


def test_render_hw_matches_golden_without_writing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(REPO_ROOT)
    data = _ok("render_hw", {"path": "examples/hw/s3-datalogger.yaml"})
    assert data["schema"] == "verino-render/1"
    assert data["written"] == []
    golden = GOLDEN / "s3-datalogger"
    expected = {
        p.relative_to(golden).as_posix(): _text(p).replace("{VERSION}", __version__)
        for p in (golden / "gen").rglob("*")
    }
    assert data["files"] == expected


def test_render_hw_out_dir(tmp_path: Path) -> None:
    text = _text(EXAMPLES / "s3-datalogger.yaml")
    data = _ok("render_hw", {"yaml": text, "out_dir": str(tmp_path)})
    assert sorted(data["written"]) == sorted((tmp_path / f).as_posix() for f in data["files"])
    assert _text(tmp_path / "gen" / "pins.hpp") == data["files"]["gen/pins.hpp"]


def test_render_hw_refuses_auto_pins(tmp_path: Path) -> None:
    text = _text(SOLVE / "01-i2c-sensor" / "input.yaml")
    data = _ok("render_hw", {"yaml": text, "out_dir": str(tmp_path)})
    assert data["files"] == {}
    assert data["written"] == []
    assert data["reason"]
    assert any(f["id"] == "E-PIN-005" for f in data["report"]["findings"])
    assert not (tmp_path / "gen").exists()


# stdio


def test_verino_mcp_runs_over_stdio() -> None:
    params = StdioServerParameters(command=sys.executable, args=["-m", "verino", "mcp"])

    async def run() -> dict[str, Any]:
        async with Client(params) as client:
            names = {t.name for t in (await client.list_tools()).tools}
            assert names == TOOLS
            result = await client.call_tool("list_boards", {"keyword": "relay"})
            assert result.structured_content is not None
            return result.structured_content

    data = anyio.run(run)
    assert [p["part"] for p in data["parts"]] == ["grove-relay"]
