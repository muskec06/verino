# Status

<!-- Rewritten by the coding session at the end of every session (/handoff). Keep under ~80 lines. -->

- **Design version:** 0.2
- **Phase:** 0 — Pin-planner
- **Current task:** T5 — `verino pins check` / `pins render` (planning)
- **Last updated:** 2026-11-18

## Done since last design sync

- T1 — Repository skeleton (PR #1). CLI `verino` / `vrn`; CI `lint` + `test` (3.11/3.13 × Ubuntu/Windows) + `dco`.
- T2 — `hardware.yaml` schema `verino-hw/1` (PR #2). Typed model with `file:line:col`; reference doc `docs/hardware-yaml.md`.
- T3 — ESP32-S3 chip data (PR #4).
  - `chipdata/chips/esp32s3.yaml`: generated `soc_caps` block (extractor over ESP-IDF v6.1.1 headers) + hand-written `manual` block with provenance; sources in `chipdata/sources.yaml`.
  - WROOM-1 module files (N8R8, N16R8, ...); drift test against a local IDF tree (`VERINO_IDF_PATH`).
- T4 — Rule catalog (PR #5 merged; part 2 in PR #7, re-opened because #6 merged into the #5 branch instead of `main`).
  - Engine: one module per rule ID, `chipdata/rules/rules.yaml` catalog, `trigger`/`clean` fixture per rule, `ack` handling (`I-ACK-001` for unused acks), status `ok`/`warnings`/`error` → exit 0/1/2.
  - 22 IDs: `E-YAML-001`, `E-SCHEMA-001`, `E-REF-001`, `W-REF-002`, `E-PIN-001..004`, `E-RSV-001`, `E-RSV-002`, `W-RSV-003`, `W-RSV-004`, `E-ADC-001`, `W-ADC-003`, `E-PERIPH-001`, `I-ACK-001`, `W-STRAP-001`, `E-STRAP-002`, `W-STRAP-003`, `I-STRAP-004`, `W-BOOT-010`, `E-VOLT-001`.
  - Part manifests `chipdata/parts/`: BME280, DS18B20, WS2812B, HC-SR04 (community source), Grove Relay v1.2.
  - New chip facts: S3 general-purpose SPI hosts, IO voltage limit, ADC2/Wi-Fi sharing (IDF v6.1.1 docs).
  - 200 tests pass (1 skipped without `VERINO_IDF_PATH`); ruff and `mypy --strict` clean. Reference doc `docs/rules.md`.

## Change notes awaiting review

- [0001 Device pin shorthand](changes/0001-device-pin-shorthand.md) — `applied-pending-review`.
- [0002 Chip data layout and ESP-IDF v6 sources](changes/0002-chipdata-layout-idf6.md) — `applied-pending-review`.
- [0003 `uses` field in hardware.yaml](changes/0003-hardware-uses-field.md) — `applied-pending-review`.
- [0004 ESP32-only Level 1 rules move to T8](changes/0004-esp32-only-rules-to-t8.md) — `applied-pending-review`.

## Open questions for the design session

- 0001: should bus pins accept the device pin shorthand too?
- 0002: is the `soc_caps` / `manual` two-block chip file the layout to keep for ESP32 (T8) and later chips?
- 0003: in Phase 1, who owns `uses` — the user, or the drivers/components that imply Wi-Fi/BLE/deep sleep?
- Strap severity policy: which strap pins are `error` vs `warning` vs `info` is set per pin in `manual.strapping`; confirm the policy.
- `I-STRAP-004` means "use of an info-level strap pin" (not "conflict on one"): GPIO3's `boot_safe` is `any`, so a conflict can never occur. Not yet released; confirm before T5 ships.
- `E-ADC-002` (ESP32 ADC2 unusable with Wi-Fi): IDF v6.1.1 `adc_oneshot.rst` lists ESP32 with S2/S3 as *shared* under arbitration. Re-evaluate in T8; it may become `W-ADC-003` only.

## Risks / blockers

- PR #7 (T4 part 2) must merge before T5 starts.
- `chipdata/chips/esp32s3.yaml`: GPIO39 entry still `TODO(verify)`.
- No board data yet (DevKitC-1, DevKitC) until T8; `board:` references produce `W-REF-002`.
- `examples/hw/s3-greenhouse.yaml` intentionally reports `E-VOLT-001` (HC-SR04 echo at 5 V into GPIO16) and `E-PIN-004`; kept as a demo.
- Branch protection: required checks must list all 8 `lint`/`test` matrix variants plus `dco`; none configured, so auto-merge is unavailable.
- `LICENSE` is not bundled into the sdist/wheel; resolve before publishing to PyPI.
- Local sources live outside the repo (`verino-sources/`, see its `SOURCES.md`); the IDF drift test is skipped in CI.
