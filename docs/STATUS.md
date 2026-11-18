# Status

<!-- Rewritten by the coding session at the end of every session (/handoff). Keep under ~80 lines. -->

- **Design version:** 0.2
- **Phase:** 0 — Pin-planner
- **Current task:** T2 — `hardware.yaml` schema (`verino-hw/1`) (not started)
- **Last updated:** 2026-11-18

## Done since last design sync

- T1 — Repository skeleton (PR #1, branch `t1-repo-skeleton`, CI green: 4× `lint`, 4× `test`, `dco`).
  - `tools/verino/pyproject.toml`: hatchling backend, Python ≥ 3.11, deps and dev deps per plan, version `0.1.0.dev0` single-sourced in `src/verino/__init__.py`.
  - CLI `verino` / `vrn` → `verino.cli:app`: `--version`, empty `pins` group; `python -m verino` works.
  - Empty subpackages `model/ rules/ solve/ render/ chipdata/ mcp/`; `.gitkeep` placeholders for `schemas/`, `chipdata/{chips,modules,boards,rules,parts}/`, `skills/pin-planner/`, `examples/hw/`.
  - `.github/workflows/ci.yml`: `lint` + `test` on 3.11/3.13 × Ubuntu/Windows; `dco` job on PRs (DCO GitHub App not installed).
  - Tests: `tests/test_cli.py` (3 tests).

## Change notes awaiting review

- (none)

## Open questions for the design session

- (none)

## Risks / blockers

- Branch protection: matrix jobs report as `lint (<os>, <python>)` / `test (<os>, <python>)`; required checks must list all 8 variants plus `dco` (or add an aggregate job later).
- `LICENSE` is at the repo root and not bundled into the sdist/wheel; resolve before publishing to PyPI.
- T3 needs the local ESP-IDF path and ESP32-S3 + WROOM-1 datasheets from the maintainer.
