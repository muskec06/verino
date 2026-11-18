# 0007: MCP tool inputs and outputs

- **Status:** applied-pending-review
- **Date:** 2026-11-18
- **Design version:** 0.2
- **Phase / task:** Phase 0 / T7
- **Affects:** `docs/tr/architecture.md` → "Donanım araçları ve pin-planner skill'i (Faz 0)" (tool table)

## What the design says

`list_boards` takes a chip or keyword and returns boards, revisions and modules. `solve_pins` takes the board, interfaces, devices and locked pins. `check_hw` and `render_hw` take `hardware.yaml`. The MCP server uses the same commands as the CLI.

## What we need instead

- Every file tool (`check_hw`, `solve_pins`, `render_hw`) takes exactly one of `path` (a file on disk) or `yaml` (the file text).
- `solve_pins` takes a `hardware.yaml` with `auto` pins (change note 0006), not a separate request format, and also returns the solved file text.
- `render_hw` returns the generated files as text; it writes only when given `out_dir`.
- Results are the CLI's `--json` documents (`verino-report/1`, `verino-solve/1`, `verino-render/1`) plus a few fields: `written`, `reason`, `yaml`, `files`.
- `list_boards` returns `verino-boards/1`, which lists boards, modules (chip, part number, flash, PSRAM) and part manifests (interface kinds, pin roles).
- Tools write only when asked: `write: true` (path only) or `out_dir`.

## Why

- Claude Desktop has no project directory, so text in and text out is needed there. Claude Code works on files, so it uses `path`.
- With one input format, the agent writes the same file the user later checks, solves and renders.
- The skill needs the part names and pin roles to write `devices` without guessing. Adding them to `list_boards` keeps the tool set at the designed four.

## Impact

- New output schema name `verino-boards/1`; the other documents are unchanged.
- Board revisions are not listed until board data exists (T8).

## Questions for the design session

- Should `list_boards` be renamed (e.g. `list_hardware`) now that it also lists parts?
