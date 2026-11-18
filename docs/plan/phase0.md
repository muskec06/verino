# Phase 0 plan — Pin-planner

Sources: `docs/architecture.md` and, for detail, `docs/tr/architecture.md` (sections on `hardware.yaml`, the pin/module/board model, hardware validation rules and the pin-planner skill).

Goal: a deterministic tool, usable by Claude over MCP, that writes, validates and derives `hardware.yaml` for ESP32-S3 and ESP32.

Rules: tasks run in order; one branch/PR per task; a task is ticked only when every "Done when" item holds.

---

## T1 — Repository skeleton

- [x] Folder layout per `AGENTS.md` → "Repository layout"; `README.md`, `LICENSE` (Apache-2.0), `.gitignore`, `.gitattributes`, `.editorconfig`, `CHANGELOG.md` and community files already present; extend `.gitignore` only if needed.
- [x] `tools/verino/pyproject.toml`: Python ≥ 3.11; deps `ruamel.yaml`, `jsonschema`, `typer`, `jinja2`, `mcp`; dev deps `pytest`, `ruff`, `mypy`. Project URLs point to `https://verino.dev`.
- [x] `verino --version` and an empty `verino pins` command group; `vrn` alias entry point.
- [x] GitHub Actions: `lint` (ruff, mypy) and `test` (pytest) on Python 3.11 and 3.13, on Ubuntu and Windows; DCO check (skip if the DCO GitHub App is installed). Job names must stay `lint` and `test` (used by branch protection).

**Done when:** `pip install -e ".[dev]"` then `verino --version` works; CI is green.

## T2 — `hardware.yaml` schema (`verino-hw/1`)

- [x] `schemas/verino-hw-1.schema.json` with `schema, source, board, board_rev, module, chip_rev, hw_rev, memory, buses, devices, ack, reserved, validation`.
- [x] Pin assignment object `{ pin, origin, locked? }`, `origin ∈ {schematic, user, board_default, solver, cubemx}`.
- [x] `src/verino/model/`: YAML → typed model (dataclasses) keeping line/column info for messages.
- [x] `examples/hw/`: at least 3 valid and 3 invalid examples; schema tests.

**Done when:** invalid examples produce messages with line numbers; round-trip writing preserves comments (tested).

## T3 — ESP32-S3 chip data

- [ ] `src/verino/chipdata/extract_soc_caps.py`: takes an ESP-IDF source path; extracts valid GPIOs, output-capable mask, ADC/RTC channels and peripheral counts from `soc_caps.h` and related soc headers. Output carries `provenance: soc_caps` and the IDF version.
- [ ] `chipdata/chips/esp32s3.yaml`: generated part + hand-written part (strapping GPIO0/3/45/46, USB GPIO19/20, UART0 GPIO43/44, flash GPIO26–32, octal PSRAM GPIO33–37, `boot_behavior`). Every hand-written field cites datasheet name + page/section.
- [ ] `chipdata/modules/`: `esp32-s3-wroom-1-n8r8`, `esp32-s3-wroom-1-n16r8` (flash/PSRAM size and mode, internally used pins).
- [ ] `schemas/chipdata.schema.json` + tests.

**Done when:** data passes the schema; no hand-written field lacks a reference (a test enforces this); uncertain values are `TODO(verify)` and listed at the end of this file.

**Needed from the user:** local ESP-IDF path (v5.5 or 6.x), ESP32-S3 datasheet and ESP32-S3-WROOM-1 module datasheet PDFs.

## T4 — Rule catalog (level 1 + selected level 2)

- [ ] `chipdata/rules/rules.yaml`: rule ID, severity, short name, description, `provenance`, phase.
- [ ] Level 1: pin exists, reserved pin, input-only, no internal pull, analog channel, ADC2 + Wi-Fi, peripheral count.
- [ ] Level 2: strapping via `reset_imposes` (e.g. `E-STRAP-002`), actuator boot safety (`W-BOOT-010`), 5 V check (`io_voltage`).
- [ ] `chipdata/parts/`: minimal device manifests (pin roles, `io_voltage`, `reset_imposes`, `actuator`) for bme280, ds18b20, ws2812, relay module, hc-sr04.
- [ ] Intentional exceptions via `ack` (reason required).
- [ ] `fixtures/<ID>/trigger.yaml` and `clean.yaml` for every rule; parametrized test.

**Done when:** every rule has both fixtures and they pass; an acknowledged rule appears as "acknowledged" in the report.

## T5 — `verino pins check` and `verino pins render`

- [ ] `check`: human output + `--json`; exit code 0 clean, 1 warnings, 2 errors. `--write` fills `reserved` and `validation` and writes the checksum.
- [ ] `render`: `gen/pins.hpp` (`constexpr` constants, compiles standalone in Arduino and ESP-IDF), `sdkconfig.defaults` fragment (flash, PSRAM, CPU), `partitions.csv`, `pinout.md`.
- [ ] Memory checks: partitions fit in flash, two app partitions when OTA is selected, PSRAM mode matches the module.
- [ ] Golden-file tests (byte-identical output).

**Done when:** `pins.hpp` generated from an example compiles in an ESP-IDF project (verified once on the user's machine; note the result here).

## T6 — `verino pins solve`

- [ ] Input: board, requested interfaces/devices, `locked` pins. Output: assignments + a reason for each.
- [ ] Method: backtracking + scoring. Preferences: board defaults, IO_MUX pins for fast SPI, keep UART0 and USB free, ADC1 when Wi-Fi is used, RTC pins when deep sleep is used.
- [ ] Solver output always passes `check` (tested).
- [ ] No solution: explain which constraints conflict.

**Done when:** 10-scenario test set; deterministic solutions; `locked` pins never change.

## T7 — Pin-planner skill and MCP server

- [ ] `src/verino/mcp/`: `list_boards`, `solve_pins`, `check_hw`, `render_hw`; they call the CLI functions.
- [ ] `skills/pin-planner/SKILL.md`: flow (board choice → schematic described in text → interfaces/devices → solve → check → render); calls tools, embeds no rules.
- [ ] MCP setup notes for Claude Code and Claude Desktop in `README.md`.

**Done when:** an end-to-end conversation with Claude produces a valid `hardware.yaml` and `pins.hpp` (transcript in `docs/plan/demo-t7.md`).

## T8 — ESP32 and two boards

- [ ] `chipdata/chips/esp32.yaml` (strapping GPIO0/2/5/12/15, flash GPIO6–11, input-only GPIO34–39, GPIO36/39 spurious-interrupt erratum tied to `chip_rev`).
- [ ] `chipdata/modules/`: ESP32-WROOM-32 and ESP32-WROVER (GPIO16/17 PSRAM).
- [ ] `chipdata/boards/esp32-s3-devkitc-1.yaml` (RGB LED alias: v1.0 GPIO48, v1.1 GPIO38) and `chipdata/boards/esp32-devkitc.yaml`.
- [ ] All rules tested with fixtures on both chips.

**Done when:** all rules green on both chips; board aliases resolve.

---

## Gate 0 (Phase 0 → Phase 1)

- [ ] Technical: level 1 rules and tests green; check, render, solve, MCP and skill work.
- [ ] Usage: used in at least 3 real projects and caught at least one pin or memory error. Log each use as one line in `docs/plan/usage-log.md` (date, project, board, error caught).

If the gate is not met, do not start Phase 1; re-evaluate scope.

## Open questions affecting Phase 0

- [ ] Boot-time pin behaviour measurement: which boards, which logic analyzer, which procedure (`measured` provenance).

## TODO(verify)

<!-- Values from T3/T8 whose source could not be confirmed: file, field, why uncertain -->

## Parked

<!-- Out-of-scope ideas worth keeping: date, short description, target phase -->

- 2026-11-18: `hardware.yaml` `source: {kind: cubemx, ...}` and `source: devicetree`; T2 schema accepts only `native` (Phase 3 / deferred).
- 2026-11-18: Octal flash mode (`opi`) in `memory.flash.mode` for modules with octal flash; not needed by Phase 0 modules (Phase 0b).

---

## Suggested first message for Claude Code

> Read `AGENTS.md` and `docs/plan/phase0.md`. Plan T1 (repository skeleton): list the files you will create and the contents of `pyproject.toml`, then implement after my approval. Stay in scope.
