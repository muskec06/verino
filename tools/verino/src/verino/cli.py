"""Command-line interface for Verino (``verino`` / ``vrn``)."""

from pathlib import Path
from typing import Annotated

import typer

from verino import __version__
from verino.model import load_hardware
from verino.report import to_json, to_text, write_back
from verino.rules import check

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
