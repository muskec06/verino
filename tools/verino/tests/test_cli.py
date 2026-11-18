"""Tests for the CLI skeleton: version flag, pins group and entry points."""

from importlib.metadata import entry_points

from typer.testing import CliRunner

from verino import __version__
from verino.cli import app

runner = CliRunner()


def test_version_flag_prints_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == f"verino {__version__}"


def test_pins_group_exists() -> None:
    result = runner.invoke(app, ["pins", "--help"])
    assert result.exit_code == 0
    assert "Pin planning" in result.stdout


def test_verino_and_vrn_share_the_same_entry_point() -> None:
    scripts = {ep.name: ep.value for ep in entry_points(group="console_scripts")}
    assert scripts["verino"] == "verino.cli:app"
    assert scripts["vrn"] == "verino.cli:app"
