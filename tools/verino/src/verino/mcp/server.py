"""MCP server for ``verino mcp``: the CLI's check, solve and render functions as tools.

The tools hold no rules or decisions of their own. Each one loads the input, calls the
function the CLI calls and returns the same JSON document as the CLI's ``--json`` output
(``verino-report/1``, ``verino-solve/1``, ``verino-render/1``), plus the text the client
needs when it has no file system.

Input is either ``path`` (a ``hardware.yaml`` on disk; Claude Code) or ``yaml`` (the file
text; Claude Desktop). Nothing is written unless the call asks for it (``write`` or
``out_dir``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from verino import __version__
from verino.chipdata.db import ChipDB
from verino.model import LoadResult, load_hardware, parse_hardware
from verino.render import render_loaded, write_outputs
from verino.render import to_dict_result as render_dict
from verino.report import to_dict, write_back
from verino.rules import check
from verino.solve import solve
from verino.solve.output import solved_text
from verino.solve.output import to_dict_result as solve_dict

BOARDS_SCHEMA = "verino-boards/1"
TEXT_FILE = "hardware.yaml"

INSTRUCTIONS = """\
Verino checks and plans ESP32 pin assignments in a hardware.yaml file.
The tools decide; explain their findings by rule ID and never choose pins yourself.
Typical flow: list_boards -> write hardware.yaml with `auto` pins -> solve_pins ->
check_hw -> render_hw. Pass `path` when the file is on disk, otherwise `yaml` text.
"""

_READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)
_MAY_WRITE = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)


def _load(path: str | None, yaml: str | None) -> tuple[LoadResult, Path | None]:
    if (path is None) == (yaml is None):
        raise ToolError("give either path or yaml, not both")
    if path is not None:
        file = Path(path)
        if not file.is_file():
            raise ToolError(f"{path}: file not found")
        return load_hardware(file), file
    assert yaml is not None
    return parse_hardware(yaml, TEXT_FILE), None


def _matches(keyword: str | None, *texts: str) -> bool:
    return keyword is None or any(keyword.lower() in t.lower() for t in texts)


def list_boards(db: ChipDB, chip: str | None = None, keyword: str | None = None) -> dict[str, Any]:
    """Boards, modules and part manifests in the chip data, optionally filtered."""
    modules = []
    for name in db.modules():
        m = db.module(name)
        if m is None or (chip is not None and m.chip != chip):
            continue
        if not _matches(keyword, m.module, m.part_number, m.chip):
            continue
        modules.append(
            {
                "module": m.module,
                "chip": m.chip,
                "part_number": m.part_number,
                "flash": m.flash_size,
                "psram": m.psram_size,
            }
        )
    parts = []
    for name in db.parts():
        p = db.part(name)
        if p is None or not _matches(keyword, p.part, p.title, *p.kinds):
            continue
        parts.append(
            {
                "part": p.part,
                "title": p.title,
                "kinds": list(p.kinds),
                "pins": {role: pin.direction for role, pin in p.pins.items()},
            }
        )
    boards = [{"board": b} for b in db.boards() if _matches(keyword, b)]
    return {
        "schema": BOARDS_SCHEMA,
        "chipdata": db.version(),
        "boards": boards,
        "modules": modules,
        "parts": parts,
    }


def check_hw(
    db: ChipDB, path: str | None = None, yaml: str | None = None, write: bool = False
) -> dict[str, Any]:
    """Run every rule; with ``write`` also update the file's reserved and validation blocks."""
    loaded, file = _load(path, yaml)
    if not write:
        return to_dict(check(loaded, db))
    if file is None:
        raise ToolError("write needs path")
    outcome = write_back(file, db)
    data = to_dict(outcome.report)
    data["written"] = outcome.written
    data["reason"] = outcome.reason or None
    return data


def solve_pins(
    db: ChipDB,
    path: str | None = None,
    yaml: str | None = None,
    write: bool = False,
    reassign: bool = False,
) -> dict[str, Any]:
    """Choose a pin for every ``auto`` slot; returns the solved file text as ``yaml``."""
    loaded, file = _load(path, yaml)
    if write and file is None:
        raise ToolError("write needs path")
    result = solve(loaded, db, reassign=reassign)
    data = solve_dict(result)
    text = solved_text(loaded, result) if result.status == "solved" else None
    if write and file is not None and text is not None:
        file.write_text(text, encoding="utf-8", newline="\n")
    data["yaml"] = text
    data["written"] = bool(write and text is not None)
    return data


def render_hw(
    db: ChipDB, path: str | None = None, yaml: str | None = None, out_dir: str | None = None
) -> dict[str, Any]:
    """Render the outputs; returns their text as ``files`` and writes them below ``out_dir``."""
    loaded, _ = _load(path, yaml)
    result = render_loaded(loaded, db)
    written = write_outputs(result, Path(out_dir)) if out_dir is not None else []
    data = render_dict(result, written)
    data["files"] = result.files
    return data


def build_server(db: ChipDB | None = None) -> MCPServer:
    """The MCP server with the four Phase 0 tools."""
    chipdb = db if db is not None else ChipDB()
    server = MCPServer(
        "verino",
        version=__version__,
        instructions=INSTRUCTIONS,
        website_url="https://verino.dev",
        log_level="WARNING",
    )

    @server.tool(name="list_boards", annotations=_READ_ONLY)
    def _list_boards(chip: str | None = None, keyword: str | None = None) -> dict[str, Any]:
        """List boards, modules (chip, flash, PSRAM) and device parts known to Verino.

        `chip` (e.g. esp32s3) and `keyword` (case-insensitive text) narrow the list.
        Use module and part names exactly as returned when writing hardware.yaml.
        """
        return list_boards(chipdb, chip, keyword)

    @server.tool(name="check_hw", annotations=_MAY_WRITE)
    def _check_hw(
        path: str | None = None, yaml: str | None = None, write: bool = False
    ) -> dict[str, Any]:
        """Check a hardware.yaml against every rule (same as `verino pins check --json`).

        Give `path` (file on disk) or `yaml` (file text). `write: true` (path only) also
        writes the tool-owned reserved and validation blocks into the file. Returns status
        ok/warning/error and findings with rule ID, location, message, why and fix.
        Explain findings by rule ID; do not restate rules from memory.
        """
        return check_hw(chipdb, path, yaml, write)

    @server.tool(name="solve_pins", annotations=_MAY_WRITE)
    def _solve_pins(
        path: str | None = None,
        yaml: str | None = None,
        write: bool = False,
        reassign: bool = False,
    ) -> dict[str, Any]:
        """Choose a GPIO for every pin written as `auto` (same as `verino pins solve --json`).

        Give `path` (file on disk) or `yaml` (file text). Locked and user pins are kept;
        `reassign: true` also moves unlocked pins with origin: solver. `write: true` (path
        only) writes the chosen pins into the file. Returns each assignment with its
        reasons, the check report after solving, and the solved file text as `yaml`.
        """
        return solve_pins(chipdb, path, yaml, write, reassign)

    @server.tool(name="render_hw", annotations=_MAY_WRITE)
    def _render_hw(
        path: str | None = None, yaml: str | None = None, out_dir: str | None = None
    ) -> dict[str, Any]:
        """Render gen/pins.hpp, sdkconfig.defaults, partitions.csv and pinout.md.

        Same as `verino pins render --json`, plus the file texts as `files`. Give `path`
        or `yaml`; `out_dir` writes gen/ below that directory, otherwise nothing is
        written. Nothing is rendered while the check reports errors.
        """
        return render_hw(chipdb, path, yaml, out_dir)

    return server
