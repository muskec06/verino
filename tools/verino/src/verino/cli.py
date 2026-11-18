"""Command-line interface for Verino (``verino`` / ``vrn``)."""

import typer

from verino import __version__

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
