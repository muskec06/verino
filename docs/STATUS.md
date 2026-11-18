# Status

<!-- Rewritten by the coding session at the end of every session (/handoff). Keep under ~80 lines. -->

- **Design version:** 0.2
- **Phase:** 0 — Pin-planner
- **Current task:** T3 — ESP32-S3 chip data (not started; blocked on inputs, see Risks)
- **Last updated:** 2026-11-18

## Done since last design sync

- T1 — Repository skeleton (PR #1, merged).
  - `tools/verino` package (hatchling, Python ≥ 3.11, version `0.1.0.dev0`); CLI `verino` / `vrn` with `--version` and an empty `pins` group.
  - CI: `lint` + `test` on 3.11/3.13 × Ubuntu/Windows, `dco` sign-off check on PRs.
- T2 — `hardware.yaml` schema `verino-hw/1` (PR #2, merged).
  - `schemas/verino-hw-1.schema.json`; pin assignment `{pin, origin, locked?}`; unknown fields rejected everywhere.
  - `verino.model`: ruamel round-trip load → schema validation → reference checks → frozen dataclasses with `file:line:col`. Tools write only `reserved` / `validation`.
  - Examples: 3 valid (`examples/hw/`), 4 invalid (`examples/hw/invalid/`). 38 tests; valid examples round-trip byte-identically.
  - Reference doc `docs/hardware-yaml.md`.

## Change notes awaiting review

- [0001 Device pin shorthand](changes/0001-device-pin-shorthand.md) — `applied-pending-review`. Device pins accept `pin: GPIO4` (= `origin: user`); bus pins require the full object.

## Open questions for the design session

- 0001: should bus pins accept the shorthand too?
- New diagnostic IDs `E-YAML-001` (invalid YAML / duplicate key) and `E-SCHEMA-001` (schema or reference error), approved by the maintainer; to be registered in `rules.yaml` in T4. Confirm they belong in the rule catalog.
- Schema choices not spelled out in the design (small, local): `module` required and `board` optional; device `kind ∈ {adc, gpio, onewire, pwm}` (`gpio` added for relays / HC-SR04); bus kinds limited to `i2c`, `spi`, `uart` for now; `memory.*.origin ∈ {module, user}`.
- Parked in `docs/plan/phase0.md`: non-native `source` (cubemx, devicetree) and octal flash mode `opi`.

## Risks / blockers

- T3 needs from the maintainer: local ESP-IDF path (v5.5 or 6.x), ESP32-S3 datasheet PDF, ESP32-S3-WROOM-1 module datasheet PDF.
- Branch protection: matrix checks report as `lint (<os>, <python>)` / `test (<os>, <python>)`; required checks must list all 8 variants plus `dco`.
- `LICENSE` (repo root) is not bundled into the sdist/wheel; resolve before publishing to PyPI.
- Example pin choices in `examples/hw/` are not yet checked against chip rules (T4/T5).
