# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Design documents (design v0.2), Phase 0 plan, contribution and community files.
- Python package skeleton (`tools/verino`) with the `verino` / `vrn` CLI: `--version` and an empty `pins` command group.
- CI workflow: `lint` (ruff, mypy) and `test` (pytest) on Python 3.11 and 3.13, Ubuntu and Windows; DCO sign-off check on pull requests.
- `hardware.yaml` schema `verino-hw/1` (`schemas/verino-hw-1.schema.json`), typed model with line/column locations (`verino.model`), round-trip writing that keeps comments, examples in `examples/hw/` and a format reference (`docs/hardware-yaml.md`).
- Diagnostics `E-YAML-001` and `E-SCHEMA-001`.
- ESP32-S3 chip data (`chipdata/chips/esp32s3.yaml`), ESP32-S3-WROOM-1 N8R8/N16R8 module data, source registry and `schemas/chipdata.schema.json`; `verino.chipdata.extract_soc_caps` reads ESP-IDF v6 headers; reference `docs/chipdata.md`.
- Rule engine (`verino.rules.check`), rule catalog `chipdata/rules/rules.yaml` with trigger/clean fixtures, Level 1 rules for ESP32-S3 and acknowledgements; `uses` field in `hardware.yaml`; typed chip data access (`verino.chipdata.db`); chip data ships in the wheel.
- Part manifests (`chipdata/parts/`: bme280, ds18b20, ws2812, hc-sr04, grove-relay) and Level 2 rules: strapping (`W-STRAP-001`, `E-STRAP-002`, `W-STRAP-003`, `I-STRAP-004`), actuator boot safety (`W-BOOT-010`) and IO voltage (`E-VOLT-001`).
- `verino pins check`: human and `--json` output (`verino-report/1`), exit codes 0/1/2, and `--write` to fill `reserved` and `validation` with a content checksum; reference `docs/cli.md`.
- `verino pins render`: `gen/pins.hpp`, `gen/sdkconfig.defaults`, `gen/partitions.csv` and `gen/pinout.md` from a file without errors (jinja2 templates); golden-file tests; clean example `examples/hw/s3-datalogger.yaml`.
- `verino pins solve`: fills `auto` pins by backtracking + scoring, using the rule set itself to test every candidate; prefers SPI IO_MUX pins, RTC pins with deep sleep and avoids strapping/shared pins; `--write`, `--reassign`, `--json`; explains unsatisfiable slots. `auto` pin value and rule `E-PIN-005`; `soc_caps.spi_iomux` from ESP-IDF `spi_pins.h`; ten solver scenarios with golden output.
- Memory rules `E-MEM-001` (partitions fit in flash), `E-MEM-002` (OTA layout), `E-MEM-003` (memory matches the module) and `W-VAL-001` (stale `validation`); ESP-IDF partition data `chipdata/idf/partitions.yaml` with `verino.chipdata.extract_partitions`; `memory.partitions.preset` limited to the ESP-IDF built-in tables.
