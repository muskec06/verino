"""Command-line interface for Verino (``verino`` / ``vrn``)."""

import json
from pathlib import Path
from typing import Annotated

import typer

from verino import __version__
from verino.model import load_hardware
from verino.render import render_file, write_outputs
from verino.render import to_dict_result as render_dict
from verino.report import to_json, to_text, write_back
from verino.rules import check
from verino.solve.output import solve_file
from verino.solve.output import to_json as solve_json
from verino.solve.output import to_text as solve_text

app = typer.Typer(
    name="verino",
    no_args_is_help=True,
    add_completion=False,
    help="Verino hardware toolkit.",
)
pins_app = typer.Typer(no_args_is_help=True, help="Pin planning: check, render, solve.")
app.add_typer(pins_app, name="pins")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"verino {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Verino hardware toolkit."""


@pins_app.command("check")
def pins_check(
    file: Annotated[
        Path,
        typer.Argument(exists=True, dir_okay=False, readable=True, help="hardware.yaml to check."),
    ],
    as_json: Annotated[bool, typer.Option("--json", help="Print the report as JSON.")] = False,
    write: Annotated[
        bool,
        typer.Option("--write", help="Write the reserved and validation blocks into the file."),
    ] = False,
) -> None:
    """Check a hardware.yaml file. Exit code: 0 ok, 1 warnings, 2 errors."""
    if write:
        outcome = write_back(file)
        report = outcome.report
        if not outcome.written:
            typer.echo(f"{file.as_posix()}: not written: {outcome.reason}", err=True)
    else:
        report = check(load_hardware(file))
    typer.echo(to_json(report) if as_json else to_text(report), nl=False)
    raise typer.Exit(report.exit_code)


@pins_app.command("render")
def pins_render(
    file: Annotated[
        Path,
        typer.Argument(exists=True, dir_okay=False, readable=True, help="hardware.yaml to render."),
    ],
    out: Annotated[
        Path | None,
        typer.Option("-o", "--out", help="Output directory (default: the file's directory)."),
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Print the result as JSON.")] = False,
) -> None:
    """Write gen/pins.hpp, gen/sdkconfig.defaults, gen/partitions.csv and gen/pinout.md.

    Nothing is written when the check reports errors (exit code 2).
    """
    result = render_file(file)
    written = write_outputs(result, out if out is not None else file.parent)
    code = 0 if result.files else 2
    if as_json:
        typer.echo(json.dumps(render_dict(result, written), indent=2, ensure_ascii=False))
    else:
        if result.report.findings:
            typer.echo(to_text(result.report), nl=False)
        for path in written:
            typer.echo(f"wrote {path}")
        if not result.files:
            typer.echo(f"{file.as_posix()}: not rendered: {result.reason}", err=True)
    raise typer.Exit(code)


@pins_app.command("solve")
def pins_solve(
    file: Annotated[
        Path,
        typer.Argument(exists=True, dir_okay=False, readable=True, help="hardware.yaml to solve."),
    ],
    write: Annotated[
        bool, typer.Option("--write", help="Write the chosen pins into the file.")
    ] = False,
    reassign: Annotated[
        bool,
        typer.Option("--reassign", help="Also move unlocked pins with origin: solver."),
    ] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Print the result as JSON.")] = False,
) -> None:
    """Choose pins for every 'auto' slot. Exit code: 0 solved, 2 no solution or invalid file."""
    result = solve_file(file, write=write, reassign=reassign)
    typer.echo(solve_json(result) if as_json else solve_text(result), nl=False)
    raise typer.Exit(result.exit_code)


@app.command("mcp")
def mcp_server() -> None:
    """Run the MCP server on stdio (tools: list_boards, check_hw, solve_pins, render_hw)."""
    from verino.mcp import build_server

    build_server().run("stdio")
