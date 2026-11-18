# 0005: ESP-IDF partition data, chipdata version and partition presets

- **Status:** applied-pending-review
- **Date:** 2026-11-18
- **Design version:** 0.2
- **Phase / task:** Phase 0 / T5
- **Affects:** `docs/tr/architecture.md` → `hardware.yaml` format (`memory.partitions.preset`, `validation`), section "Bellek bölümü (ESP32)"; `AGENTS.md` → repository layout (`chipdata/`)

## What the design says

- `memory.partitions` has a `preset` (example: `ota_2app_littlefs`) and/or a `custom` list; `verino` checks that partitions fit in flash and that OTA has two app partitions.
- `validation.chipdata` looks like `esp32s3@2026.11`; `validation.checksum` is a sha256, and a changed checksum forces re-validation.
- `chipdata/` holds `chips/`, `modules/`, `boards/`, `rules/` and `parts/`.

## What we need instead

- New folder `chipdata/idf/` with `partitions.yaml` (schema `verino-partitions/1`):
  - `generated.presets`: the ESP-IDF built-in tables `singleapp`, `singleapp_large`, `two_ota`, `two_ota_large`, extracted by `python -m verino.chipdata.extract_partitions` from `components/partition_table/*.csv` of ESP-IDF v6.1.1.
  - `manual.table`: partition table offset 0x8000, table size 0x1000, sector size 0x1000, app alignment 0x10000 (IDF `partition-tables.rst`).
  - `manual.ota`: OTA needs `ota_0`, `ota_1` and an OTA data partition (IDF `ota.rst`).
- `memory.partitions.preset` is restricted to those four names in `verino-hw-1.schema.json`; an unknown preset is `E-SCHEMA-001`. When `custom` is present it is the table and `preset` is only a label. The design example `ota_2app_littlefs` is not an IDF table and is not offered.
- `chipdata/sources.yaml` gains a top-level `version` (`2026.11`); `validation.chipdata` is `<chip>@<version>`.
- `validation.checksum` is the sha256 of the canonical JSON (sorted keys, no whitespace) of the document without `reserved` and `validation`. Comment and formatting changes do not change it.
- New rule IDs: `E-MEM-001` (partitions do not fit in flash), `E-MEM-002` (incomplete OTA layout), `E-MEM-003` (memory differs from the module), `W-VAL-001` (`validation` checksum is stale).

## Why

- Partition offsets, alignment and OTA requirements are ESP-IDF facts; principle 3 needs them sourced, and principle 2 puts them in data. They are not chip facts, so they do not belong in `chips/`.
- Named presets need a definition; the IDF built-in tables are the ones users already know from `menuconfig`.
- A checksum over the data, not the text, lets users edit comments without a stale `validation` block.

## Impact

- `chipdata/` gets one more subfolder; it ships in the wheel with the rest.
- Adding a preset is a data change plus a schema enum change.
- Bumping `chipdata/sources.yaml` `version` is a manual step when chip data changes.

## Questions for the design session

- Should Verino offer its own presets (e.g. OTA + LittleFS) on top of the IDF tables?
- Should `chipdata` version be bumped by hand or derived (content hash)?
