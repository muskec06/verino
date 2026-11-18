# AGENTS.md — Verino

Root instructions for every agent (Claude Code, Codex, ...) and human contributor working in this repository.

- Architecture overview: `docs/architecture.md` (full Turkish document: `docs/tr/architecture.md`)
- Decisions: `docs/adr/`
- Current work plan: `docs/plan/phase0.md`
- Session status and design sync: `docs/STATUS.md`, `docs/changes/`, `docs/design-sync.md`

## The project in one sentence

A tested, chip-independent C++ driver layer for ESP32 (later STM32) that agents can read and compose, plus the hardware toolkit that feeds it. Vendor SDKs (ESP-IDF, STM32Cube) stay underneath; Verino does **not** build a new RTOS, package manager or build system.

**Positioning:** not the most drivers, but a verified hardware layer agents don't have to guess about.

## Current phase: Phase 0 — Pin-planner

Only Phase 0 work is in scope. Tasks and acceptance criteria are in `docs/plan/phase0.md`. Read it before starting a task; tick the task when done.

Phase 0 delivers the hardware commands of the Python `verino` CLI:

- `verino pins check <hardware.yaml>` — report with stable rule IDs (`--json` supported).
- `verino pins render <hardware.yaml>` — `gen/pins.hpp`, `sdkconfig.defaults` fragment, `partitions.csv`, `pinout.md`.
- `verino pins solve` — pin assignment by backtracking + scoring.
- MCP server (`list_boards`, `solve_pins`, `check_hw`, `render_hw`) and `skills/pin-planner/`.

Phase 0 chips: **ESP32-S3** and **ESP32**. Boards: **ESP32-S3-DevKitC-1** and **ESP32-DevKitC**.

### Out of scope in Phase 0

These were deliberately deferred. Unless the user explicitly asks, do not write code for them, create folders for them, or leave "might be useful later" stubs:

- C++ core, HAL, adapters, drivers (Phase 1).
- ESP32-C3 and XIAO data, catalog site, `verino hw detect`, Wokwi `diagram.json`, visual pin picker (Phase 0b).
- Net extraction from schematic images/PDFs (not planned), KiCad import (end of Phase 1), CubeMX import (Phase 3).
- Zephyr (deferred), compat tier, C API, networking package.

If you find an out-of-scope need, don't build it: add one line to "Parked" at the end of `docs/plan/phase0.md`.

## Non-negotiable principles

1. **The LLM talks, the tool decides.** Pin, memory and compatibility rules live in deterministic code, never in skill prose.
2. **Data before code.** Chip, module, board and rule knowledge lives in YAML; code reads data.
3. **No invented hardware facts.** Every fact in chip/board data has a `provenance` (`soc_caps`, `datasheet`, `errata`, `community`, `measured`); `datasheet` entries cite document name + page/section. If you are not sure, do not write the value: leave `TODO(verify)` and ask the user. In this repo a wrong pin fact is worse than a missing one.
4. **Every rule is tested.** Each rule has at least one "must trigger" and one "must not trigger" fixture.
5. **Rule IDs are stable.** `E-` error, `W-` warning, `I-` info (e.g. `E-STRAP-002`, `W-BOOT-010`). A published ID is never reused or redefined.
6. **Schema first.** Any change to the `hardware.yaml` format updates the JSON Schema (`schemas/verino-hw-1.schema.json`), fixtures and docs together.
7. **Decisions that break a principle need an ADR** (`docs/adr/NNNN-*.md`). Propose it to the user before changing architecture.

## Repository layout (Phase 0)

```text
AGENTS.md  CLAUDE.md  README.md  LICENSE  CHANGELOG.md  CONTRIBUTING.md  CODE_OF_CONDUCT.md  SECURITY.md
.gitignore  .gitattributes  .editorconfig
.claude/commands/          # /change-note, /handoff
.github/                   # CI workflows, issue and PR templates
docs/
  architecture.md          # English overview
  adr/                     # architecture decision records
  plan/phase0.md           # tasks, acceptance criteria, parked items
  design/                  # future-phase design docs (read only when a task links them)
  changes/                 # change notes from coding sessions
  STATUS.md  DESIGN_VERSION  design-sync.md
  tr/architecture.md       # full architecture document (Turkish, v0.2)
schemas/
  verino-hw-1.schema.json  # hardware.yaml schema
chipdata/
  chips/  modules/  boards/
  rules/                   # rules.yaml + fixtures/<RULE-ID>/{trigger,clean}.yaml
  parts/                   # minimal device manifests for Phase 0 (pin roles, io_voltage, reset_imposes)
tools/verino/              # Python package and CLI
  pyproject.toml
  src/verino/  cli.py  model/  rules/  solve/  render/  chipdata/  mcp/
  tests/
skills/pin-planner/SKILL.md
examples/hw/               # example hardware.yaml files
```

Ask before creating a new top-level folder.

## Technical choices (Phase 0)

- **Python ≥ 3.11.** Package `tools/verino`, import name `verino`, CLI `verino` (short alias `vrn`).
- **YAML:** `ruamel.yaml` round-trip (keeps user comments and key order; `hardware.yaml` is written by both humans and tools).
- **Validation:** `jsonschema` for structure; semantic rules in `src/verino/rules/`, one registered function/module per rule ID.
- **CLI:** `typer`. Every command supports `--json`; human and JSON output come from the same data model.
- **Templates:** `jinja2`.
- **MCP:** official Python MCP SDK; tools call the same functions as the CLI and contain no logic of their own.
- **Tests:** `pytest`; fixture-based rule tests are parametrized.
- **Quality:** `ruff` (lint + format), `mypy --strict` on `src/verino`.
- Justify every new dependency in the PR description. No heavy solvers (OR-Tools etc.): the decision is backtracking + scoring.

## Commands

```bash
cd tools/verino
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

pytest
pytest -k STRAP
ruff check . && ruff format --check .
mypy src/verino

verino pins check ../../examples/hw/s3-greenhouse.yaml
verino pins check ../../examples/hw/s3-greenhouse.yaml --json
verino pins render ../../examples/hw/s3-greenhouse.yaml -o /tmp/out
```

## Language and style

- **Everything in the repository is English:** code, identifiers, comments, docs, rule descriptions, user-facing messages, commit messages. The only exception is `docs/tr/`.
- Message format: file and line, what is wrong, why it matters, suggested fix. Example: `E-STRAP-002 hardware.yaml:42 GPIO12 is a strapping pin; HIGH at reset selects 1.8 V flash and the board will not boot. Fix: GPIO13 or GPIO14.`
- Output is deterministic: same input → byte-identical output (stable ordering, no timestamps).
- Only tools write the `reserved` and `validation` blocks; tools never touch user fields (including `locked: true` pins).
- Links in code, config and docs point to `https://verino.dev` or are relative. Do not hard-code `github.com/<owner>/verino`: the repository will move from `muskec06/verino` to `verino-dev/verino`.

## Workflow

1. Pick the next unticked task in `docs/plan/phase0.md`. For multi-file tasks write a short plan and show it to the user first.
2. Tests/fixtures first, then code. For a new rule: `rules.yaml` entry + two fixtures first.
3. Small, single-purpose commits. Conventional Commits (`feat(rules): add E-STRAP-002`), signed off (`git commit -s`, DCO).
4. Definition of done: tests green, `ruff` + `mypy` clean, related docs/plan updated, new rule or schema field has fixtures.
5. Tick the task in the plan; put out-of-scope findings under "Parked".

## Design ownership and change notes

The design is maintained in separate design sessions; see `docs/design-sync.md`.

- **Do not edit** `docs/architecture.md`, `docs/tr/`, `docs/adr/` or `docs/design/` (typos and broken links excepted).
- When implementation must differ from the design, write a change note in `docs/changes/` (`/change-note` in Claude Code) and continue only if the work is not blocked; otherwise ask the user.
- At the end of every session, rewrite `docs/STATUS.md` (`/handoff` in Claude Code).
- Read only the current phase plan by default. Read `docs/design/` documents only when a task links to them.

## Stop and ask when

- the source of a chip/board fact is unclear;
- a schema or rule ID would change;
- a new dependency or top-level folder is needed;
- a solution would conflict with a principle above.
